#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import collections
import ast
import fnmatch
import numbers
import re
from six import string_types
import pyparsing as pp

from .match_environ import MatchContext

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
    if pathes is None:
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

    def eval_one(self, input_value, context):
        raise NotImplemented

    def eval(self, input_value, context):
        # 시작하기 전에 한번 검사해서 flat_nested_object 에 의한 generator 생성을 차단
        if isinstance(input_value, numbers.Number) or isinstance(input_value, string_types):
            return self.eval_one(input_value, context)

        for name, value in flat_nested_object(input_value):
            if isinstance(input_value, list) and len(input_value) and isinstance(input_value[0], dict):
                break
            matched, matched_value = self.eval_one(value, context)
            if matched:
                return matched, matched_value
        return False, None


class TextMatcher(BaseMatcher):
    def __init__(self, value, term_match_op=TERM_MATCH_OP_EQUAL):
        self.term_match_op = term_match_op
        self.value = value.value
        self.quoted = False

        if isinstance(value, QuotedString):
            self.quoted = True

    def __repr__(self):
        return 'TextMatcher:{}'.format(self.value)

    def count(self, input_value, context):
        if not isinstance(input_value, string_types):
            input_value = str(input_value)

        # keyword set 설정이 있는 경우 반영한다.
        if context.has_keyword_set(self.value):
            count, matched_value = context.count_keyword_set(self.value, input_value)
            return count, matched_value
        else:
            count = input_value.count(self.value)
            return count, self.value

    def eval_one(self, input_value, context):
        if not self.quoted:
            if isinstance(input_value, bool):
                # If input_value is bool value, try boolean match
                # XXX: isinstance(True, numbers.Number) == True. So we try boolean first.
                try:
                    if self.value.lower() in ['true', 'false']:
                        boolean_value = self.value.lower() == 'true'
                        return boolean_value == input_value, input_value
                except ValueError:
                    pass
            elif isinstance(input_value, numbers.Number):
                # If input_value is numeric value, try Int/Float match
                try:
                    return int(self.value) == int(input_value), input_value
                except ValueError:
                    pass

                try:
                    return (abs(float(str(self.value))) - abs(float(input_value))) < 1e-09, input_value
                except ValueError:
                    pass

        if not isinstance(input_value, string_types):
            input_value = str(input_value)

        # keyword set 설정이 있는 경우 반영한다.
        if context.has_keyword_set(self.value):
            if self.term_match_op == TERM_MATCH_OP_CONTAIN:
                r = context.search_keyword_set(self.value, input_value)
            else:
                r = context.match_keyword_set(self.value, input_value)

            if r:
                return r
            else:
                return False, None

        if '*' in self.value or '?' in self.value:
            return fnmatch.fnmatch(input_value, self.value), input_value

        if self.term_match_op == TERM_MATCH_OP_CONTAIN:
            return self.value in input_value, self.value
        else:
            return self.value == input_value, self.value

    def get_value(self):
        return self.value


class RegexpMatcher(BaseMatcher):
    def __init__(self, value):
        self.value = value.value
        self.pattern = None

        options = value.options
        flags = 0
        if 'i' in options:
            flags = flags | re.IGNORECASE
        self.pattern = re.compile(self.value, flags)

    def __repr__(self):
        return 'RegexpMatcher:{}'.format(self.value)

    def count(self, input_value, context):
        if not isinstance(input_value, string_types):
            input_value = str(input_value)

        # keyword set 설정이 있는 경우 반영한다.
        pattern = self.pattern
        if context.has_keyword_set(self.value):
            pattern = context.expand_regexp(self.value)

        last_matched = ''
        count = 0
        start = 0
        while True:
            m = pattern.search(input_value[start:])
            if not m:
                break
            last_matched = m.group()
            start += m.start() + 1
            count += 1
        return count, last_matched

    def eval_one(self, input_value, context):
        if not isinstance(input_value, string_types):
            input_value = str(input_value)

        # keyword set 설정이 있는 경우 반영한다.
        if context.has_keyword_set(self.value):
            expanded_regexp = context.expand_regexp(self.value)
            m = expanded_regexp.search(input_value)
        else:
            m = self.pattern.search(input_value)

        if m:
            return True, m.group()
        else:
            return False, None

    def get_value(self):
        return self.value


def build_text_matcher(value, term_match_op):
    if isinstance(value, RQuotedString):
        return RegexpMatcher(value)
    else:
        return TextMatcher(value, term_match_op)


class MultipleTextMatcher(BaseMatcher):
    def __init__(self, values, term_match_op=TERM_MATCH_OP_EQUAL):
        self.matchers = list(map(lambda v: build_text_matcher(v, term_match_op), values))

    def __repr__(self):
        matchers_text = ','.join(map(lambda t: t.get_value(), self.matchers))
        return 'MultipleTextMatcher: {}'.format(matchers_text)

    def eval_one(self, input_value, context):
        for matcher in self.matchers:
            matched, matched_value = matcher.eval_one(input_value, context)
            if matched:
                return matched, matched_value
        return False, None


class CountingMatcher(BaseMatcher):
    def __init__(self, matcher, op, condition_value):
        self.matcher = matcher
        self.op = op
        self.condition_value = int(condition_value.value)

    def __repr__(self):
        return f'CountingMatcher({self.matcher},{self.op},{self.condition_value})'

    def count(self, value, context):
        count, matched_value = self.matcher.count(value, context)
        return count, matched_value

    def eval_one(self, input_value, context):
        return self.count(input_value, context)

    def eval(self, input_value, context):
        count = 0
        last_matched = ''

        # 시작하기 전에 한번 검사해서 flat_nested_object 에 의한 generator 생성을 차단
        if isinstance(input_value, numbers.Number) or isinstance(input_value, string_types):
            count, last_matched = self.eval_one(input_value, context)
        else:
            for name, value in flat_nested_object(input_value):
                if isinstance(input_value, list) and len(input_value) and isinstance(input_value[0], dict):
                    break
                e_count, e_last_matched = self.eval_one(value, context)
                if e_count > 0:
                    count += e_count
                    last_matched = e_last_matched

        if self.op == '<=':
            return count <= self.condition_value, last_matched
        elif self.op == '<':
            return count < self.condition_value, last_matched
        elif self.op == '>=':
            return count >= self.condition_value, last_matched
        elif self.op == '>':
            return count > self.condition_value, last_matched
        elif self.op == '=':
            pass
        return count == self.condition_value, last_matched


class CodeMatcher:
    def __init__(self, expression):
        self.expression = expression
        self.compiled = __builtins__['compile'](expression, '_expression_matcher', 'eval')
        parsed = ast.parse(expression)
        self.variable_names = [node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)]

    def __repr__(self):
        return 'CodeMatcher({})'.format(self.expression)

    def create_local(self, input_value, context):
        local = {}
        functions = context.environ.get_functions()

        local.update(functions)
        local['this'] = input_value
        return local

    def is_no_args_function(self, local):
        first = self.variable_names[0] if len(self.variable_names) == 1 else None
        if first and callable(local.get(first)):
            return True
        else:
            return False

    def call_single_function(self, local, this):
        first = self.variable_names[0]
        return local[first](this)

    def eval(self, input_value, context):
        this = input_value
        local = self.create_local(input_value, context)
        try:
            if self.is_no_args_function(local):
                ret = self.call_single_function(local, this)
            else:
                ret = eval(self.compiled, {}, local)
        except (AttributeError, TypeError) as e:
            return False, None
        except Exception as e:
            raise e
        return ret, ret


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
            return input_value <= condition_value, input_value
        elif op == '<':
            return input_value < condition_value, input_value
        elif op == '>=':
            return input_value >= condition_value, input_value
        elif op == '>':
            return input_value > condition_value, input_value
        elif op == '=':
            pass
        return input_value == condition_value, input_value

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
            return False, None
        try:
            return self._eval(self.value, self.op, input_value)
        except TypeError as e:
            return False, None


class RangeMatcher(BaseMatcher):
    def __init__(self, incl, start, stop):
        self.incl = incl
        try:
            start = float(start)
            stop = float(stop)
            self.is_float = True
        except Exception:
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
                return False, None
        elif not isinstance(input_value, str):
            input_value = str(input_value)

        try:
            if self.incl:
                return self.start <= input_value <= self.stop, input_value
            return self.start < input_value < self.stop, input_value
        except TypeError as e:
            return False, None


class TermMatcher:
    def __init__(self, field_name, field_value):
        self.field_name = field_name
        self.field_value = field_value

    def __repr__(self):
        return 'TermMatcher({}:{})'.format(self.field_name, self.field_value)

    def eval(self, context):
        input_value = context.get(self.field_name)

        if input_value is None:
            return False, None

        matched, matched_value = self.field_value.eval(input_value, context)
        if matched:
            context.add_result((self.field_name, input_value, matched_value))
        return matched, matched_value


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

    def get_local(self, context):
        functions = context.environ.get_functions()
        local = dict(context.get_dict())
        local.update(functions)
        return DictOrObject(local)

    def eval(self, context):
        try:
            local = self.get_local(context)
            ret = eval(self.compiled, {}, local)
        except (AttributeError, TypeError) as e:
            return False, None
        except Exception as e:
            raise e

        return ret, ret


class ExistsMatcher:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def __repr__(self):
        return 'ExistsMatcher({})'.format(self.variable_name)

    def eval(self, context):
        return context.exists(self.variable_name), self.variable_name


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
        matched, matched_value = self.term.eval(context)
        if not matched:
            if not context.get_result():
                context.add_result(('NOT', 'NOT', 'NOT'))
            return True, 'NOT'
        else:
            return False, None


class OrMatcher:
    def __init__(self, left, right):
        self.left, self.right = left, right

    def __repr__(self):
        return 'OR({},{})'.format(self.left, self.right)

    def eval(self, context):
        lmatched, lmatched_value = self.left.eval(context)
        if lmatched:
            return lmatched, lmatched_value
        rmatched, rmatched_value = self.right.eval(context)
        if rmatched:
            return rmatched, rmatched_value
        return False, None


class AndMatcher:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return 'AND({}, {})'.format(self.left, self.right)

    def eval(self, context):
        lmatched, lmatched_value = self.left.eval(context)
        if not lmatched:
            return False, None
        rmatched, rmatched_value = self.right.eval(context)
        if not rmatched:
            return False, None
        return True, (lmatched_value, rmatched_value)


def build_binary_matcher(l, class_object):
    left = l[0]
    op_ = None
    for idx in range(2, len(l), 2):
        right = l[idx]
        op_ = class_object(left, right)
        left = op_
    return op_


def escape_regexp_term(tokens):
    regexp = tokens[0]

    # strip start/end
    regexp = regexp[1:-1]

    # replace \/ to /
    regexp = regexp.replace('\\/', '/')

    if len(tokens) == 2:
        return RQuotedString(regexp, tokens[1])
    else:
        return RQuotedString(regexp, '')


def escape_raw_regexp_term(tokens):
    regexp = tokens[1]
    if len(tokens) == 4:
        return RQuotedString(regexp, tokens[-1])
    else:
        return RQuotedString(regexp, '')


#
# Grammar
#
def get_parser(implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
    COLON, LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(pp.Literal, ':[]{}~^')
    LPAR, RPAR = map(pp.Suppress, '()')
    AND_, OR_, NOT_, TO_ = map(pp.CaselessKeyword, 'AND OR NOT TO'.split())
    LTE, LT, GTE, GT, EQ  = map(pp.Literal, ['<=', '<', '>=', '>', '='])
    RAW_REGEXP_DELIMETER = pp.Literal('/~/')
    COUNT_NAME = 'COUNT'
    START_OF_CODE = '!'

    expression = pp.Forward()

    valid_keyword = pp.Regex(r'[a-zA-Z_*@][a-zA-Z0-9_*@.\[\]]*')
    valid_code = pp.Regex(r'([^\s]+)').setParseAction(lambda t: ValidText(t[0]))
    valid_text = pp.Regex(r'([^\s\)]+)').setParseAction(lambda t: ValidText(t[0]))
    quoted_string = pp.QuotedString('"').setParseAction(lambda t: QuotedString(t[0]))
    rquoted_string = (pp.QuotedString('/', escChar='\\', escQuote='\\/', unquoteResults=False)
                      + pp.Optional(pp.Regex(r'[i]'))) \
            .setParseAction(lambda t: escape_regexp_term(t))
    rquoted_string2 = (RAW_REGEXP_DELIMETER + pp.SkipTo(RAW_REGEXP_DELIMETER) + RAW_REGEXP_DELIMETER + pp.Optional(pp.Regex(r'[i]'))) \
            .setParseAction(lambda t: escape_raw_regexp_term(t))

    field_text_value = (quoted_string | rquoted_string2 | rquoted_string | valid_text )('text_field_value') \
        .setParseAction(lambda t: build_text_matcher(t[0], term_match_op))

    field_operate_value = ((LTE | LT | GTE | GT | EQ) + (valid_text | quoted_string))('operate_field_value') \
        .setParseAction(lambda t: Operator(t[0], t[1]))

    range_text_value = (pp.Regex(r'([^\s\]\}]+)'))
    incl_range_search = pp.Group(LBRACK + range_text_value + TO_ + range_text_value + RBRACK)
    incl_range_search.setParseAction(lambda t: RangeMatcher(True, t[0][1], t[0][3]))
    excl_range_search = pp.Group(LBRACE + range_text_value + TO_ + range_text_value + RBRACE)
    excl_range_search.setParseAction(lambda t: RangeMatcher(False, t[0][1], t[0][3]))
    field_range_value = (incl_range_search | excl_range_search)('range_field_value')

    multiple_field_text_value = (quoted_string | rquoted_string | valid_text)
    field_multiple_value = (LPAR + pp.OneOrMore(multiple_field_text_value) + RPAR)('multiple_field_value') \
        .setParseAction(lambda t: MultipleTextMatcher(t, term_match_op))

    field_count_value = (COUNT_NAME + LPAR + field_text_value + RPAR + (LTE | LT | GTE | GT | EQ) + (valid_text)) \
        .setParseAction(lambda t: CountingMatcher(t[1], t[2], t[3]))

    field_code_string = (quoted_string | valid_code)('code_field_value')
    field_code_value = (START_OF_CODE + field_code_string) \
        .setParseAction(lambda t: CodeMatcher(t[1].value))

    field_name = valid_keyword
    field_value = (field_code_value | field_count_value |
                   field_multiple_value | field_operate_value |
                   field_range_value | field_text_value)
    field_term = pp.Group(field_name('field_name') + COLON + field_value) \
        .setParseAction(lambda t: build_term_matcher(t[0][0], t[0][2]))

    term = pp.Forward()
    term << (field_term | pp.Group(LPAR + expression + RPAR).setParseAction(lambda t: t[0]))

    not_expression = ((NOT_ | '!').setParseAction(lambda: "NOT"), 1, pp.opAssoc.RIGHT, lambda t: NotMatcher(t[0][1]))
    if implicit_bin_op == IMPLICIT_BIN_OP_AND:
        and_expression = (pp.Optional(AND_ | '&&')
                          .setParseAction(lambda: "AND"),
                          2,
                          pp.opAssoc.LEFT,
                          lambda t: build_binary_matcher(t[0], AndMatcher))
        or_expression = ((OR_ | '||')
                         .setParseAction(lambda: "OR"),
                         2,
                         pp.opAssoc.LEFT,
                         lambda t: build_binary_matcher(t[0], OrMatcher))
    else:
        and_expression = ((AND_ | '&&')
                          .setParseAction(lambda: "AND"),
                          2,
                          pp.opAssoc.LEFT,
                          lambda t: build_binary_matcher(t[0], AndMatcher))
        or_expression = (pp.Optional(OR_ | '||')
                         .setParseAction(lambda: "OR"),
                         2,
                         pp.opAssoc.LEFT,
                         lambda t: build_binary_matcher(t[0], OrMatcher))
    expression << pp.infixNotation(term, [ not_expression, and_expression, or_expression, ])
    return expression


PREBUILT_PARSERS = {}
for bin_op in [IMPLICIT_BIN_OP_OR, IMPLICIT_BIN_OP_AND]:
    PREBUILT_PARSERS[bin_op] = {}
    for match_op in [TERM_MATCH_OP_EQUAL, TERM_MATCH_OP_CONTAIN]:
        PREBUILT_PARSERS[bin_op][match_op] = get_parser(bin_op, match_op)


def build_json_matcher(expr, implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
    if implicit_bin_op not in PREBUILT_PARSERS or term_match_op not in PREBUILT_PARSERS[implicit_bin_op]:
        raise ValueError('No parser for ({}, {})'.format(implicit_bin_op, term_match_op))

    expression = PREBUILT_PARSERS[implicit_bin_op][term_match_op]
    matcher, = expression.parseString(expr, parseAll=True)
    return matcher


JsonMatchValue = collections.namedtuple('JsonMatchedValue', ['field_name', 'query_value', 'matched_value'])


class JsonMatchResult:
    def __init__(self, matched_list):
        self.matched = list(map(lambda matched: JsonMatchValue(*matched), matched_list))

    def group(self, idx=0):
        return self.matched[idx]

    def groups(self):
        return self.matched


class JsonMatcher():
    def __init__(self, expression, implicit_bin_op=IMPLICIT_BIN_OP_AND, term_match_op=TERM_MATCH_OP_EQUAL):
        try:
            self.matcher = build_json_matcher(expression, implicit_bin_op, term_match_op)
        except pp.ParseBaseException as e:
            raise JsonMatcherParseException(e)

    def match(self, j):
        context = MatchContext(j)
        return self.match_with_context(context)

    def match_with_context(self, context):
        matched, matched_value = self.matcher.eval(context)
        if matched:
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
           'JsonMatcher', 'JsonMatchResult',
           'IMPLICIT_OR', 'IMPLICIT_AND', 'TERM_MATCH_EQUAL', 'TERM_MATCH_CONTAIN']
