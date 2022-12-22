from __future__ import print_function, unicode_literals

import re

import pydash

KEYWORD_SET_PREFIX = '@@'
DEFAULT_KEYWORD_SET_NAME = 'keyword'


class KeywordSet(object):
    def __init__(self, name, keyword_list=None):
        self.name = name
        self.regexp = None
        self.regexp_exact = None
        self.keyword_list = keyword_list if keyword_list else []

    def add_keyword(self, keyword):
        self.keyword_list.append(keyword)

    def get_regexp_str(self, exact=False):
        cleaned_list = list(filter(None, self.keyword_list))
        regexp_str = '(' + '|'.join(map(lambda keyword: re.escape(keyword), cleaned_list)) + ')'
        if exact:
            regexp_str = '^' + regexp_str + '$'
        return regexp_str

    def get_regexp(self):
        if not self.regexp:
            self.regexp = re.compile(self.get_regexp_str())
        return self.regexp

    def get_regexp_exact(self):
        if not self.regexp_exact:
            self.regexp_exact = re.compile(self.get_regexp_str(True))
        return self.regexp_exact

    def expand_regexp(self, base_regexp):
        name = KEYWORD_SET_PREFIX + '{' + self.name + '}'
        my_regexp = self.get_regexp_str()
        return base_regexp.replace(name, my_regexp)

    def search(self, value):
        return self.get_regexp().search(value)

    def match(self, value):
        return self.get_regexp_exact().match(value)


class MatchEnvironment(object):
    def __init__(self):
        self.keyword_sets = {}

    def put_keyword_set(self, name, keyword_set):
        self.keyword_sets[name] = keyword_set

    def get_keyword_set(self, name):
        return self.keyword_sets.get(name)

    def with_default_keyword_set(self, keyword_set):
        new_environment = MatchEnvironment()
        new_environment.keyword_sets = dict(self.keyword_sets)
        new_environment.keyword_sets[DEFAULT_KEYWORD_SET_NAME] = keyword_set
        return new_environment


EMPTY_ENVIRONMENT = MatchEnvironment()


class MatchContext:
    _contains_dummy_default_object = object()

    def __init__(self, j, environ=None):
        self.j = j
        self.result = []
        if not environ:
            self.environ = EMPTY_ENVIRONMENT
        else:
            self.environ = environ

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

    def get(self, field_name, j=None, default=None):
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

    KEYWORD_SET_NAME_RE = re.compile(KEYWORD_SET_PREFIX + r'{([^}]*)}')

    def extract_keyword_set_names(self, query):
        return self.KEYWORD_SET_NAME_RE.findall(query)

    def extract_keyword_set_name(self, query):
        names = self.extract_keyword_set_names(query)
        if not names:
            return
        return names[0]

    def has_keyword_set(self, query):
        names = self.extract_keyword_set_names(query)
        for name in names:
            if not self.environ.get_keyword_set(name):
                return False
        return True

    def expand_regexp(self, base_regexp):
        names = self.extract_keyword_set_names(base_regexp)
        regexp = base_regexp
        for name in names:
            keyword_set = self.environ.get_keyword_set(name)
            regexp = keyword_set.expand_regexp(regexp)
        return re.compile(regexp)

    def search_keyword_set(self, term, input_value):
        name = self.extract_keyword_set_name(term)
        if not name:
            return False

        keyword_set = self.environ.get_keyword_set(name)
        if not keyword_set:
            return False
        return bool(keyword_set.search(input_value))

    def match_keyword_set(self, term, input_value):
        name = self.extract_keyword_set_name(term)
        if not name:
            return False

        keyword_set = self.environ.get_keyword_set(name)
        if not keyword_set:
            return False
        return bool(keyword_set.match(input_value))


__all__ = ['KeywordSet', 'MatchContext', 'MatchEnvironment']
