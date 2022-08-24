#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import collections
import ast
import fnmatch
import numbers
import re
from six import string_types
import pydash
import pyparsing as pp
import itertools

IMPLICIT_BIN_OP_AND = 'AND'
IMPLICIT_BIN_OP_OR = 'OR'
TERM_MATCH_OP_EQUAL = 'EQUAL'
TERM_MATCH_OP_CONTAIN = 'CONTAIN'


pp.ParserElement.enablePackrat()


class JsonMatcherBaseException(Exception):
    pass


class JsonMatcherParseException(JsonMatcherBaseException):
    def __init__(self, original_exception):
        self.original_exception = original_exception

    def __repr__(self):
        return 'JsonMatcherParseException({})'.format(repr(self.original_exception))


ValidText = collections.namedtuple('ValidText', ['value'])
QuotedString = collections.namedtuple('QuotedString', ['value'])
RQuotedString = collections.namedtuple('RQuotedString', ['value', 'options'])


def flat_nested_object(o, pathes=None, depth=0, max_depth=10):
    if depth >= max_depth:
        return
    if pathes == None:
        pathes = []
    if isinstance(o, list):
        for idx, item in enumerate(o):
            new_pathes = pathes + ['[{}]'.format(idx)]
            for name, value in flat_nested_object(item, new_pathes, depth + 1, max_depth):
                yield name, value
    elif isinstance(o, dict):
        for inner_key, inner_value in o.items():
            new_pathes = pathes + ['.{}'.format(inner_key)]
            for name, value in flat_nested_object(inner_value, new_pathes, depth + 1, max_depth):
                yield name, value
    else:
        name = ''.join(pathes)
        if name.startswith('.'):
            name = name[1:]
        yield name, o
    return


# list / dictionary 가 입력되는 경우 nested 된 객체를 풀어서 접근한다.
class BaseMatcher:
    def __getitem__(self, key):
        """XXX: python2 에서 [0] 과 같은 접근은 __getitem__ 이 발생하는데, Python3 에서는 TypeError 가 발생
                pyparsing 에서 현재 특정 영역에서 AttributeError 를 처리하지 않아서 제대로 처리되지 않아
                일단 TypeError 를 발생하도록 우회
        """
        raise TypeError

    def eval(self, input_value, context):
        # 시작하기 전에 한번 검사해서 flat_nested_object 에 의한 generator 생성을 차단
        if isinstance(input_value, numbers.Number) or isinstance(input_value, string_types):
            return self.eval_one(input_value, context)
        for name, value in flat_nested_object(input_value):
            if isinstance(input_value , list) and len(input_value) and isinstance(input_value[0] , dict):
                break
            if self.eval_one(value, context):
                return True
        return False


class TextMatcher(BaseMatcher):
    def __init__(self, value, term_match_op=TERM_MATCH_OP_EQUAL):
        self.term_match_op = term_match_op
        self.value = value.value
        self.pattern = None
        self.quoted = False

        if isinstance(value, QuotedString):
            self.quoted = True
        elif isinstance(value, RQuotedString):
            options = value.options
            flags = 0
            if 'i' in options:
                flags = flags | re.IGNORECASE
            self.pattern = re.compile(self.value, flags)

    def __repr__(self):
        return 'TextMatcher:{}'.format(self.value)

    def eval_one(self, input_value, context):
        # input_value 가 숫자형태인 경우 Int/Float 변환을 통한 매치를 우선 시도한다.
        if not self.quoted and isinstance(input_value, numbers.Number):
            try:
                return int(self.value) == int(input_value)
            except ValueError:
                pass

            try:
                return (abs(float(self.value)) - abs(float(input_value))) < 1e-09
            except ValueError:
                pass
        if not isinstance(input_value, string_types):
            input_value = str(input_value)
        if self.pattern:
            return self.pattern.search(input_value)
        if '*' in self.value or '?' in self.value:
            return fnmatch.fnmatch(input_value, self.value)

        if self.term_match_op == TERM_MATCH_OP_CONTAIN:
            return self.value in input_value
        else:
            return self.value == input_value

    def get_value(self):
        return self.value


class MultipleTextMatcher(BaseMatcher):
    def __init__(self, values):
        self.matchers = list(map(lambda v: TextMatcher(v), values))

    def __repr__(self):
        matchers_text = ','.join(map(lambda t: t.get_value(), self.matchers))
        return 'MultipleTextMatcher: {}'.format(matchers_text)

    def eval_one(self, input_value, context):
        for matcher in self.matchers:
            if matcher.eval_one(input_value, context):
                context.add_result(matcher.get_value())
                return True
        return False


class Operator(BaseMatcher):
    def __init__(self, op, value):
        self.op = op

        self.value = value.value
        self.is_float = False
        self.float_value = None
        if not isinstance(value, QuotedString):
            try:
                self.float_value = float(self.value)
                self.is_float = True
            except ValueError as e:
                pass

    def __repr__(self):
        return 'Operator({}{})'.format(self.op, self.value)

    def _eval(self, condition_value, op, input_value):
        if op == '<=':
            return input_value <= condition_value
        elif op == '<':
            return input_value < condition_value
        elif op == '>=':
            return input_value >= condition_value
        elif op == '>':
            return input_value > condition_value
        elif op == '=':
            pass
        return input_value == condition_value

    def eval_one(self, input_value, context):
        #
        # input number   value number => ok
        # input number   value str    => False
        # input str      value number => ok with original value
        # input str      value str    => ok
        #
        if isinstance(input_value, numbers.Number):
            if self.is_float:
                return self._eval(self.float_value, self.op, input_value)
            return False
        try:
            return self._eval(self.value, self.op, input_value)
        except TypeError as e:
            return False


class RangeMatcher(BaseMatcher):
    def __init__(self, incl, start, stop):
        self.incl = incl
        try:
            start = float(start)
            stop = float(stop)
            self.is_float = True
        except:
            self.is_float = False
        self.start = start
        self.stop = stop

    def __repr__(self):
        start, stop = self.start, self.stop
        if self.is_float:
            start = '{:.2f}'.format(start)
            stop = '{:.2f}'.format(stop)
        if self.incl:
            return 'RangeMatcher[{}-{}]'.format(start, stop)
        return 'RangeMatcher{{{}-{}}}'.format(start, stop)

    def eval_one(self, input_value, context):
        if self.is_float:
            try:
                input_value = float(input_value)
            except ValueError as e:
                return False
        elif not isinstance(input_value, str):
            input_value = str(input_value)

        try:
            if self.incl:
                return self.start <= input_value <= self.stop
            return self.start < input_value < self.stop
        except TypeError as e:
            return False


class TermMatcher:
    def __init__(self, field_name, field_value):
        self.field_name = field_name
        self.field_value = field_value

    def __repr__(self):
        return 'TermMatcher({}:{})'.format(self.field_name, self.field_value)

    def eval(self, context):
        input_value = context.get(self.field_name)
        
        if not input_value:
            return False
        r = self.field_value.eval(input_value, context)
        if r:
            context.add_result((self.field_name, input_value))
        return r


class DictOrObject:
    def __init__(self, v):
        self.v = v

    def __contains__(self, name):
        return name in self.v

    def __getitem__(self, name):
        r = self.v.get(name)
        if r and isinstance(r, dict):
            return DictOrObject(r)
        return r

    def __getattr__(self, name):
        return self[name]

    def __repr__(self):
        return str(self.v)


class ExpressionMatcher:
    def __init__(self, expression):
        self.expression = expression
        self.compiled = __builtins__['compile'](expression, '_expression_matcher', 'eval')
        parsed = ast.parse(expression)
        self.variable_names = [node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)]

    def __repr__(self):
        return 'ExpressionMatcher({})'.format(self.expression)

    def eval(self, context):
        try:
            local = DictOrObject(context.get_dict())
            ret = eval(self.compiled, {}, local)
        except (AttributeError, TypeError):
            return False
        except Exception as e:
            raise e
        return ret


class ExistsMatcher:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def __repr__(self):
        return 'ExistsMatcher({})'.format(self.variable_name)

    def eval(self, context):
        return context.exists(self.variable_name)


def build_term_matcher(field_name, field_value):
    if field_name == '_expr_':
        return ExpressionMatcher(field_value.get_value())
    elif field_name == '_exists_':
        return ExistsMatcher(field_value.get_value())
    return TermMatcher(field_name, field_value)


class NotMatcher:
    def __init__(self, term):
        self.term = term

    def __repr__(self):
        return 'NOT({})'.format(self.term)

    def eval(self, context):
        return not self.term.eval(context)


class OrMatcher:
    def __init__(self, left, right):
        self.left, self.right = left, right

    def __repr__(self):
        return 'OR({},{})'.format(self.left, self.right)

    def eval(self, context):
        return self.left.eval(context) or self.right.eval(context)


class AndMatcher:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return 'AND({}, {})'.format(self.left, self.right)

    def eval(self, context):
        return self.left.eval(context) and self.right.eval(context)


def build_binary_matcher(l, class_object):
    left = l[0]
    op_ = None
    for idx in range(2, len(l), 2):
        right = l[idx]
        op_ = class_object(left, right)
        left = op_
    return op_


class MatchContext:
    _contains_dummy_default_object = object()

    def __init__(self, j):
        self.j = j
        self.result = []

    def exists(self, name, j=None):
        j = self.j if j is None else j
        v = self.get(name, j, self._contains_dummy_default_object)
        if isinstance(v, list):
            for i in list(self.NestedListToList(v)):
                if i is not self._contains_dummy_default_object:
                    return True
            return False
        else:
            is_dummy_object = v is self._contains_dummy_default_object
            return not is_dummy_object

    # this function convert list of lists recursively to list
    def NestedListToList(self, l):
        for i in l:
            if isinstance(i, list):
                for j in self.NestedListToList(i):
                    yield j
            else:
                yield i

    # this function convert dict object values recursively to list
    def DictToValues(self, j):
        for v in j.values():
            if isinstance(v, dict):
                for j in self.DictToValues(v):
                    yield j
            else:
                yield v

    # find the longest path exists in the json
    def find_longest_existing_path(self, field_name, j):
        if pydash.has(j, field_name):
            return field_name

        while True:
            split = field_name.rsplit(".", 1)
            if len(split) == 1 and split[0] != '':
                return None
            field_name = split[0]
            if pydash.has(j, field_name):
                break
        return field_name

    def get(self, field_name, j=None, default=''):
        j = self.j if j is None else j

        # if the field name is *, then get list of all recursive values
        if field_name == "*":
            return list(self.DictToValues(j))

        # if the field name start with * (like *.name), then run self.get on all sub values
        if field_name.startswith("*.") and (isinstance(j, list) or isinstance(j, dict)):
            values = [self.get(field_name.lstrip("*."), j, default)]
            for v in j.values():
                if isinstance(v, list):
                    for i in v:
                        values.append(self.get(field_name, i, default))
                if isinstance(v, dict):
                    values.append(self.get(field_name, v, default))
            return values

        if pydash.has(j, field_name):
            return pydash.get(j, field_name)
        else:
            # get the longest path exists in the dict
            new_field_name = self.find_longest_existing_path(field_name, j)
            new_value = pydash.get(j, new_field_name)
            if isinstance(new_value, list) and len(new_value) and isinstance(new_value[0], dict):
                return [self.get(field_name.lstrip(new_field_name)[1:], nv, default) for nv in new_value]
            elif isinstance(new_value, dict):
                return self.get(field_name.lstrip(new_field_name)[1:], new_value)

        return default

    def get_dict(self):
        return self.j

    def add_result(self, matched):
        self.result.append(matched)

    def get_result(self):
        return self.result


#
# Grammar
#
def get_parser(implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
    COLON, LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(pp.Literal, ':[]{}~^')
    LPAR, RPAR = map(pp.Suppress, '()')
    AND_, OR_, NOT_, TO_ = map(pp.CaselessKeyword, 'AND OR NOT TO'.split())
    LTE, LT, GTE, GT, EQ = map(pp.Literal, ['<=', '<', '>=', '>', '='])

    keyword = AND_ | OR_ | NOT_ | TO_

    expression = pp.Forward()

    valid_keyword = pp.Regex(r'[a-zA-Z_*@][a-zA-Z0-9_*@.\[\]]*')
    valid_text = pp.Regex(r'([^\s\)]+)').setParseAction(lambda t: ValidText(t[0]))
    quoted_string = pp.QuotedString('"').setParseAction(lambda t: QuotedString(t[0]))
    rquoted_string = (pp.QuotedString('/', escChar='\\', escQuote='\\/') + pp.Optional(pp.Regex(r'[i]'))) \
            .setParseAction(lambda t: RQuotedString(t[0], t[1]) if len(t) == 2 else RQuotedString(t[0], ''))

    field_text_value = (quoted_string | rquoted_string | valid_text )('text_field_value').setParseAction(lambda t: TextMatcher(t[0], term_match_op))

    field_operate_value = ((LTE | LT | GTE | GT | EQ) + (valid_text | quoted_string))('operate_field_value').setParseAction(lambda t: Operator(t[0], t[1]))

    range_text_value = (pp.Regex(r'([^\s\]\}]+)'))
    incl_range_search = pp.Group(LBRACK + range_text_value + TO_ + range_text_value + RBRACK)
    incl_range_search.setParseAction(lambda t: RangeMatcher(True, t[0][1], t[0][3]))
    excl_range_search = pp.Group(LBRACE + range_text_value + TO_ + range_text_value + RBRACE)
    excl_range_search.setParseAction(lambda t: RangeMatcher(False, t[0][1], t[0][3]))
    field_range_value = (incl_range_search | excl_range_search)('range_field_value')

    multiple_field_text_value = (quoted_string | rquoted_string | valid_text)
    field_multiple_value = (LPAR + pp.OneOrMore(multiple_field_text_value) + RPAR)('multiple_field_value').setParseAction(lambda t: MultipleTextMatcher(t))

    field_name = valid_keyword
    field_value = (field_multiple_value | field_operate_value | field_range_value | field_text_value)
    field_term = pp.Group(field_name('field_name') + COLON + field_value).setParseAction(lambda t: build_term_matcher(t[0][0], t[0][2]))

    term = pp.Forward()
    term << (field_term | pp.Group(LPAR + expression + RPAR).setParseAction(lambda t: t[0]))

    not_expression = ((NOT_ | '!').setParseAction(lambda: "NOT"), 1, pp.opAssoc.RIGHT, lambda t: NotMatcher(t[0][1]))
    if implicit_bin_op == IMPLICIT_BIN_OP_AND:
        and_expression = (pp.Optional(AND_ | '&&').setParseAction(lambda: "AND"), 2, pp.opAssoc.LEFT, lambda t: build_binary_matcher(t[0], AndMatcher))
        or_expression = ((OR_ | '||').setParseAction(lambda: "OR"), 2, pp.opAssoc.LEFT, lambda t: build_binary_matcher(t[0], OrMatcher))
    else:
        and_expression = ((AND_ | '&&').setParseAction(lambda: "AND"), 2, pp.opAssoc.LEFT, lambda t: build_binary_matcher(t[0], AndMatcher))
        or_expression = (pp.Optional(OR_ | '||').setParseAction(lambda: "OR"), 2, pp.opAssoc.LEFT, lambda t: build_binary_matcher(t[0], OrMatcher))
    expression << pp.infixNotation(term, [ not_expression, and_expression, or_expression, ])
    return expression


PREBUILT_PARSERS = {}
for bin_op in [IMPLICIT_BIN_OP_OR, IMPLICIT_BIN_OP_AND]:
    PREBUILT_PARSERS[bin_op] = {}
    for match_op in [TERM_MATCH_OP_EQUAL, TERM_MATCH_OP_CONTAIN]:
        PREBUILT_PARSERS[bin_op][match_op] = get_parser(bin_op, match_op)


def build_matcher(expr, implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
    if implicit_bin_op not in PREBUILT_PARSERS or term_match_op not in PREBUILT_PARSERS[implicit_bin_op]:
        raise ValueError('No parser for ({}, {})'.format(implicit_bin_op, term_match_op))

    expression = PREBUILT_PARSERS[implicit_bin_op][term_match_op]
    matcher, = expression.parseString(expr, parseAll=True)
    return matcher


class JsonMatchResult:
    def __init__(self, matched):
        self.matched = matched

    def group(self, idx=0):
        return self.matched[idx]

    def groups(self):
        return self.matched


class JsonMatcher():
    def __init__(self, expression, implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
        try:
            self.matcher = build_matcher(expression, implicit_bin_op, term_match_op)
        except pp.ParseBaseException as e:
            raise JsonMatcherParseException(e)

    def match(self, j):
        context = MatchContext(j)
        if self.matcher.eval(context):
            r = JsonMatchResult(context.get_result())
            return r
        return


# Flags
IMPLICIT_OR = 1 << 0
IMPLICIT_AND = 1 << 1
TERM_MATCH_EQUAL = 1 << 2
TERM_MATCH_CONTAIN = 1 << 3


default_term_match_op = TERM_MATCH_OP_EQUAL


def set_default_term_match_op(term_match_option):
    global default_term_match_op
    if term_match_option == TERM_MATCH_EQUAL:
        default_term_match_op = TERM_MATCH_OP_EQUAL
    if term_match_option == TERM_MATCH_CONTAIN:
        default_term_match_op = TERM_MATCH_OP_CONTAIN


def compile(expression, flags=0):
    """compile lucene like query"""
    implicit_bin_op = IMPLICIT_BIN_OP_AND
    if flags & IMPLICIT_OR:
        implicit_bin_op = IMPLICIT_BIN_OP_OR
    if flags & IMPLICIT_AND:
        implicit_bin_op = IMPLICIT_BIN_OP_AND

    term_match_op = default_term_match_op
    if flags & TERM_MATCH_CONTAIN:
        term_match_op = TERM_MATCH_OP_CONTAIN
    if flags & TERM_MATCH_EQUAL:
        term_match_op = TERM_MATCH_OP_EQUAL

    return JsonMatcher(expression, implicit_bin_op, term_match_op)


def match(expression, j, flags=0):
    """match json with lucene like query"""
    matcher = compile(expression, flags)
    return matcher.match(j)


__all__ = ['compile', 'match',
           'JsonMatcher', 'MatchContext', 'JsonMatchResult',
           'IMPLICIT_OR', 'IMPLICIT_AND', 'TERM_MATCH_EQUAL', 'TERM_MATCH_CONTAIN']
