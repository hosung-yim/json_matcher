#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import json_matcher


def test_compile_text_term():
    assert json_matcher.compile('field_name:안녕')
    assert json_matcher.match('field_name:*안녕*', dict(field_name='여러분 안녕하세요'))

    assert json_matcher.match('field_name:"*안녕*"', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕/i', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕\\//i', dict(field_name='여러분 안녕/하세요'))

    assert not json_matcher.match('field_name:a{1,3}b', dict(field_name='aab'))
    assert json_matcher.match('field_name:/a{1,3}b/i', dict(field_name='aab'))


def test_compile_range_term():
    assert json_matcher.compile('field_name:[10 TO 30]')
    assert json_matcher.match('field_name:[10 TO 30]', dict(field_name=20))

    # convert field value to float
    assert json_matcher.match('field_name:[10 TO 30]', dict(field_name='20'))

    # string range with integer value
    assert not json_matcher.match('field_name:["10" TO "30"]', dict(field_name=20))
    assert json_matcher.match('field_name:["10" TO "30"]', dict(field_name='"20"'))


def test_compile_operate_term():
    assert json_matcher.compile('field_name:<10')
    assert json_matcher.match('field_name:<10', dict(field_name=5))
    assert not json_matcher.match('field_name:<10', dict(field_name=11))

    assert json_matcher.compile('field_name:<=10')
    assert json_matcher.match('field_name:<=10', dict(field_name=10))
    assert not json_matcher.match('field_name:<=10', dict(field_name=11))

    assert json_matcher.compile('field_name:>10')
    assert json_matcher.match('field_name:>10', dict(field_name=11))
    assert not json_matcher.match('field_name:>10', dict(field_name=5))

    assert json_matcher.compile('field_name:>=10')
    assert json_matcher.match('field_name:>=10', dict(field_name=10))
    assert not json_matcher.match('field_name:>=10', dict(field_name=5))

    # input number  value str
    assert not json_matcher.match('field_name:>="10"', dict(field_name=10))
    # input str     value number(str)
    assert json_matcher.match('field_name:>=10', dict(field_name="10"))

    d = {
        "red": "{\"res\":false,\"subs\":[\"https://0-142k.tistory.com/api\"],\"mains\":[\"https://0-142k.tistory.com/\"],\"time\":2795,\"dest\":\"https://0-142k.tistory.com/?q=%EB%8D%B0%EC%96%B4%20%EB%8D%B0%EB%B8%94%20%EB%8B%A4%EC%8B%9C%EB%B3%B4%EA%B8%B0%20%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C\",\"begin\":\"http://0-142k.tistory.com/\",\"timeout\":false}",
        "dest_url": "https://0-142k.tistory.com/?q=%EB%8D%B0%EC%96%B4%20%EB%8D%B0%EB%B8%94%20%EB%8B%A4%EC%8B%9C%EB%B3%B4%EA%B8%B0%20%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C",
        "docid": "12VYGYuncxK4v1nFSx", "service": "tistoryall", "start_url": "http://0-142k.tistory.com/",
        "dest_sld": "0-142k.tistory.com", "dest_host": "0-142k.tistory.com",
        "title": "\ub370\uc5b4 \ub370\ube14 \ub2e4\uc2dc\ubcf4\uae30 \ub2e4\uc6b4\ub85c\ub4dc", "userid": "3338219",
        "inserted_at": "2020-01-28T12:17:50"}
    assert json_matcher.match('inserted_at:>"2020-01-28T12:17:49"', d)


def test_integer_field_match():
    # input str(number parsable)     value number(str)
    assert not json_matcher.match('field_name:0', dict(field_name=50))


def test_compile_multiple_term():
    assert json_matcher.compile('field_name:(안녕 세상아 반갑다)')
    assert json_matcher.match('field_name:(*안녕* "*세상아*" *반갑다*)', dict(field_name='안녕 세상아 반갑다. 진짜로'))
    assert not json_matcher.match('field_name:(안녕 "세상아" a{1,3}b)', dict(field_name='ab'))
    assert json_matcher.match('field_name:(안녕 "세상아" /a{1,3}b/)', dict(field_name='ab'))


def test_compile_nested_par():
    assert json_matcher.compile('((A:안녕 && B:세상아) C:반갑다)')

    assert json_matcher.compile('((A:안녕 AND B:세상아) AND C:반갑다)')
    assert json_matcher.match('((A:안녕 AND B:세상아) AND C:반갑다)', dict(A='안녕', B='세상아', C='반갑다'))
    assert not json_matcher.match('((A:안녕 AND B:세상아) AND C:반갑다)', dict(A='안녕', B='세상아'))


def test_default_and():
    assert json_matcher.match('A:안녕 B:세상아 C:반갑다', dict(A='안녕', B='세상아', C='반갑다'))
    assert not json_matcher.match('A:안녕 B:세상아 C:반갑다', dict(A='Y', B='세상아', C='반갑다'))


def test_with_list():
    assert json_matcher.match('A:안녕', dict(A=['안녕', '세상아', '반갑다']))
    assert json_matcher.match('A:안녕', dict(A=dict(B=['안녕', '세상아', '반갑다'])))
    assert json_matcher.match('A:안녕', dict(A=dict(A_=dict(B=['안녕', '세상아', '반갑다']))))

    assert json_matcher.match('field_name:[10 TO 30]', dict(field_name=[1, 2, 3, 4, 5, 20]))
    assert not json_matcher.match('field_name:[10 TO 30]', dict(field_name=[1, 2, 3, 4, 5, 6]))
    assert json_matcher.match('field_name:<10', dict(field_name=[11, 20, 30, 5, 30]))
    assert not json_matcher.match('field_name:<10', dict(field_name=[11, 20, 30]))
    assert json_matcher.match('field_name:(*안녕* "*세상아*" *반갑다*)', dict(field_name=dict(B=['이건아님', '안녕 세상아 반갑다. 진짜로'])))
    assert not json_matcher.match('field_name:(안녕 "세상아" 반갑다)', dict(field_name=['A', 'B', 'C']))


def test_exists():
    assert json_matcher.match('_exists_:A', dict(A='안녕'))
    assert json_matcher.match('_exists_:A', dict(A=None))
    assert not json_matcher.match('_exists_:A', dict(B='안녕'))


def test_expression():
    assert json_matcher.match('_expr_:"A+B>10"', dict(A=10, B=20))
    assert json_matcher.match('_expr_:"A.B+B.C>10"', dict(A=dict(B=10), B=dict(C=20)))
    assert not json_matcher.match('_expr_:"A.B+B.C>10"', dict(B=dict(C=20)))
    assert not json_matcher.match('_expr_:"A.B+B.C>10"', dict(A=dict(B="A"), B=dict(C=20)))


def test_nested_field():
    assert json_matcher.match('A.B:안녕', dict(A=dict(B='안녕')))


def test_indexed_field():
    assert json_matcher.match('A.B[0]:안녕', dict(A=dict(B=['안녕'])))


def test_default_and():
    matcher = json_matcher.compile('A:안녕 B:세상아')
    assert not matcher.match(dict(A='안녕'))
    assert not matcher.match(dict(B='세상아'))
    assert matcher.match(dict(A='안녕', B='세상아'))


def test_implicit_and():
    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_AND)
    assert not matcher.match(dict(A='안녕'))
    assert not matcher.match(dict(B='세상아'))
    assert matcher.match(dict(A='안녕', B='세상아'))


def test_implicit_or():
    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_OR)
    assert matcher.match(dict(A='안녕'))
    assert matcher.match(dict(B='세상아'))
    assert matcher.match(dict(A='안녕', B='세상아'))


def test_match_result():
    # OR => short circuit
    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_OR)
    r = matcher.match(dict(A='안녕', B='세상아'))
    l = r.groups()
    assert len(l) == 1
    assert l[0] == ('A', '안녕')

    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_AND)
    r = matcher.match(dict(A='안녕', B='세상아'))
    l = r.groups()
    assert len(l) == 2
    assert l[0] == ('A', '안녕')
    assert l[1] == ('B', '세상아')


def test_field_has_data_with_wildcard():
    matcher = json_matcher.compile('field : *')
    has_field = dict(field='value')
    r = matcher.match(has_field)
    l = r.groups()
    assert len(l) == 1

    has_field_with_empty_list = dict(field=[])
    r = matcher.match(has_field_with_empty_list)
    assert not r

    has_field_with_list = dict(field=['value'])
    r = matcher.match(has_field_with_list)
    l = r.groups()
    assert len(l) == 1

    has_no_field = dict(no_field='value')
    r = matcher.match(has_no_field)
    assert not r


def test_field_match_wildcard():
    postwhildcard_matcher = json_matcher.compile('field : value*')

    r = postwhildcard_matcher.match(dict(field='value1'))
    l = r.groups()
    assert len(l) == 1

    r = postwhildcard_matcher.match(dict(field='xvalue1'))
    assert not r

    leadingwhildcard_matcher = json_matcher.compile('field : *value')

    r = leadingwhildcard_matcher.match(dict(field='value'))
    l = r.groups()
    assert len(l) == 1

    r = leadingwhildcard_matcher.match(dict(field='this is value'))
    l = r.groups()
    assert len(l) == 1

    r = leadingwhildcard_matcher.match(dict(field='this is not value1'))
    assert not r

    multiplewhildcard_matcher = json_matcher.compile('field : *value*')
    r = multiplewhildcard_matcher.match(dict(field='value'))
    l = r.groups()
    assert len(l) == 1

    r = multiplewhildcard_matcher.match(dict(field='this is value'))
    l = r.groups()
    assert len(l) == 1

    r = multiplewhildcard_matcher.match(dict(field='this is value. and more text'))
    l = r.groups()
    assert len(l) == 1

    multiplewhildcard_matcher2 = json_matcher.compile('field : *val*ue*')
    r = multiplewhildcard_matcher2.match(dict(field='valuuuuuuuuuuuuue'))
    l = r.groups()
    assert len(l) == 1


def test_list_of_jsons():
    matcher = json_matcher.compile("field.subfield:value")
    r = matcher.match(dict(field=[dict(subfield="value")]))
    l = r.groups()
    assert len(l) == 1


def test_special_char_in_field():
    matcher = json_matcher.compile("@id:30")

    r = matcher.match({"@id": 30})
    l = r.groups()
    assert len(l) == 1


def test_wildcard_in_field():
    matcher = json_matcher.compile("field.*.target:value")

    r = matcher.match({'field': {'subfield': {'target': 'value'}}})
    print(dict(field=dict(subfield=dict(target="value"))))
    assert r is not None
    l = r.groups()
    assert len(l) == 1

    matcher = json_matcher.compile("*.target:value")

    r = matcher.match(dict(field=dict(subfield=dict(target="value"))))
    l = r.groups()
    assert len(l) == 1

    matcher = json_matcher.compile("field.*:value")

    r = matcher.match(dict(field=dict(subfield=dict(target="value"))))
    l = r.groups()
    assert len(l) == 1


def test_equal_contains():
    matcher = json_matcher.compile("field:equal")

    r = matcher.match(dict(field='equal'))
    l = r.groups()
    assert len(l) == 1

    matcher = json_matcher.compile("field:*contains*")

    r = matcher.match(dict(field='contains'))
    l = r.groups()
    assert len(l) == 1


def test_equal_continas_option():
    matcher = json_matcher.compile("field:equal", json_matcher.TERM_MATCH_EQUAL)

    r = matcher.match(dict(field='This is text for equal'))
    assert not r

    matcher = json_matcher.compile("field:equal", json_matcher.TERM_MATCH_CONTAIN)

    r = matcher.match(dict(field='This is text for equal'))
    l = r.groups()
    assert len(l) == 1
