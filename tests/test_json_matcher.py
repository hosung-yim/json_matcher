#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import re

import json_matcher
from json_matcher import MatchEnvironment, MatchContext, KeywordSet, TERM_MATCH_CONTAIN


def test_compile_text_term():
    assert json_matcher.compile('field_name:안녕')
    assert json_matcher.match('field_name:*안녕*', dict(field_name='여러분 안녕하세요'))

    assert json_matcher.match('field_name:"*안녕*"', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕/i', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕\\//i', dict(field_name='여러분 안녕/하세요'))

    print(json_matcher.match('field_name:a{1,3}b', dict(field_name='aab')))
    assert not json_matcher.match('field_name:a{1,3}b', dict(field_name='aab'))
    assert json_matcher.match('field_name:/a{1,3}b/i', dict(field_name='aab'))

    assert json_matcher.match('field_name:/\\d{2,3}/', dict(field_name='123'))
    assert not json_matcher.match('field_name:/\\d{2,3}/', dict(field_name='1'))

    assert json_matcher.match('field_name:/~/a{1,3}b/~/i', dict(field_name='aab'))
    assert json_matcher.match('field_name:/~/b/{1,3}/~/i', dict(field_name='b/'))


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
    # Term Match
    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_OR)
    r = matcher.match(dict(A='안녕', B='세상아'))
    l = r.groups()
    assert len(l) == 1
    assert l[0] == ('A', '안녕', '안녕')

    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.IMPLICIT_AND)
    r = matcher.match(dict(A='안녕', B='세상아'))
    l = r.groups()
    assert len(l) == 2
    assert l[0] == ('A', '안녕', '안녕')
    assert l[1] == ('B', '세상아', '세상아')

    # Term Match (CONTAIN)
    matcher = json_matcher.compile('A:안녕 B:세상아', json_matcher.TERM_MATCH_CONTAIN)
    r = matcher.match(dict(A='안녕하세요', B='세상아 반갑다.'))
    l = r.groups()
    assert len(l) == 2
    assert l[0] == ('A', '안녕하세요', '안녕')
    assert l[1] == ('B', '세상아 반갑다.', '세상아')

    # Regexp Match
    matcher = json_matcher.compile('A:/[a-zA-Z]+/')
    r = matcher.match(dict(A='Hello World'))
    l = r.groups()
    assert len(l) == 1
    assert l[0] == ('A', 'Hello World', 'Hello')

    # Fnmatch
    matcher = json_matcher.compile('A:안녕* B:세상아*', json_matcher.TERM_MATCH_CONTAIN)
    r = matcher.match(dict(A='안녕하세요', B='세상아 반갑다.'))
    l = r.groups()
    assert len(l) == 2
    assert l[0] == ('A', '안녕하세요', '안녕하세요')
    assert l[1] == ('B', '세상아 반갑다.', '세상아 반갑다.')

    # Range Match
    matcher = json_matcher.compile('field_name:[10 TO 30]')
    r = matcher.match(dict(field_name=[1, 2, 3, 4, 5, 20]))
    l = r.groups()
    assert len(l) == 1
    assert l[0] == ('field_name', [1, 2, 3, 4, 5, 20], 20)

    # Operate
    matcher = json_matcher.compile('field_name:>10')
    r = matcher.match(dict(field_name=20))
    l = r.groups()
    assert len(l) == 1
    assert l[0] == ('field_name', 20, 20)

    # Keyword Match
    query = json_matcher.compile('field:@@{keyword}', json_matcher.TERM_MATCH_EQUAL)
    environ = MatchEnvironment()
    environ.put_keyword_set('keyword', KeywordSet('keyword', ['A', 'B', 'C']))
    context = MatchContext({'field': 'A'}, environ)
    matched = query.match_with_context(context)
    l = matched.groups()
    assert len(l) == 1
    assert l[0] == ('field', 'A', 'A')


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


def test_keyword_set_in_query():
    # - environ 을 사용하는 경우: keyword 설정등을 수행할 수 있음
    # - environ 에 전역 keyword_list map 을 설정할 수도 있으며, 개별 keyword_list 를 설정 가능
    query = json_matcher.compile('field:@@{keyword}', json_matcher.TERM_MATCH_EQUAL)
    environ = MatchEnvironment()
    environ.put_keyword_set('keyword', KeywordSet('keyword', ['A', 'B', 'C']))
    context = MatchContext({'field': 'A'}, environ)
    matched = query.match_with_context(context)
    assert matched

    # - 여러개의 keyword_set 을 등록해서 사용할 수 있다.
    keyword_set_list = [
        ('keyword1', ['A', 'B', 'C']),
        ('keyword2', ['1', '2', '3'])
    ]
    environ = MatchEnvironment()
    for keyword_name, keyword_list in keyword_set_list:
        keyword_set = KeywordSet(keyword_name, keyword_list)
        environ.put_keyword_set(keyword_name, keyword_set)
    query = json_matcher.compile('field:@@{keyword2}', json_matcher.TERM_MATCH_EQUAL)
    context = MatchContext({'field': '2'}, environ)
    matched = query.match_with_context(context)
    assert matched

    context = MatchContext({'field': 'A'}, environ)
    matched = query.match_with_context(context)
    assert not matched

    # with default keyword_set
    query = json_matcher.compile('field:@@{keyword}', json_matcher.TERM_MATCH_EQUAL)
    keyword_set = KeywordSet('keyword', ['D', 'E', 'F'])
    context = MatchContext({'field': 'D'}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert matched

    query = json_matcher.compile('field:@@{keyword}', json_matcher.TERM_MATCH_EQUAL)
    keyword_set = KeywordSet('keyword', ['D', 'E', 'F'])
    context = MatchContext({'field': '10'}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert not matched


def test_keyword_set_in_regexp_query():
    # - environ / context 를 사용하지 않는 경우
    query = json_matcher.compile('field:/prefix@@{keyword}postfix/')
    environ = MatchEnvironment()
    environ.put_keyword_set('keyword', KeywordSet('keyword', ['A', 'B', 'C']))
    context = MatchContext({'field': 'prefixApostfix'}, environ)
    matched = query.match_with_context(context)
    assert matched

    context = MatchContext({'field': 'prefixDpostfix'}, environ)
    matched = query.match_with_context(context)
    assert not matched

    # - 여러개의 keyword_set 을 등록해서 사용할 수 있다.
    keyword_set_list = [
        ('keyword1', ['A', 'B', 'C']),
        ('keyword2', ['1', '2', '3'])
    ]
    environ = MatchEnvironment()
    for keyword_name, keyword_list in keyword_set_list:
        keyword_set = KeywordSet(keyword_name, keyword_list)
        environ.put_keyword_set(keyword_name, keyword_set)
    query = json_matcher.compile('field:/prefix@@{keyword2}postfix/')
    context = MatchContext({'field': 'prefix2postfix'}, environ)
    matched = query.match_with_context(context)
    assert matched

    context = MatchContext({'field': 'prefixApostfix'}, environ)
    matched = query.match_with_context(context)
    assert not matched

    # with default keyword_set
    query = json_matcher.compile('field:/prefix@@{keyword}postfix/', json_matcher.TERM_MATCH_EQUAL)
    keyword_set = KeywordSet('keyword', ['D', 'E', 'F'])
    context = MatchContext({'field': 'prefixDpostfix'}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert matched

    query = json_matcher.compile('field:/prefix@@{keyword}postfix/', json_matcher.TERM_MATCH_EQUAL)
    keyword_set = KeywordSet('keyword', ['D', 'E', 'F'])
    context = MatchContext({'field': 'prefix10postfix'}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert not matched

    keyword_list = ['보험', '대출', '인터넷', '회생', '견적', '비교', '다운로드', '무료', '영화', '사이트', '결제', 'p2p', '웹하드', '추천',
                    '바로가기', '다시보기', '주소', '토렌토', '순위']
    keyword_set = KeywordSet('keyword', keyword_list)
    environ = MatchEnvironment()
    regexp = r'.{0,20}@@{keyword}.{0,20}@@\*\*@@http:\/\/\w{3,15}.x.com\/\d{7}"'
    query = json_matcher.compile('text:/' + regexp + '/')
    text = ('<span class="copyright_entry" style="display:block;" title="저금리 대출 안심신청 추천 햇살론@@**@@http://akcmp1szke'
            '.x.com/6866160"></span>')
    context = MatchContext({'text': text}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert matched

    text = ('<span class="copyright_entry" style="display:block;" title="저금리 대출 안심신청 추천 햇살론@@**@@http://akcmp1szke'
            '.y.com/6866160"></span>')
    context = MatchContext({'text': text}, environ.with_default_keyword_set(keyword_set))
    matched = query.match_with_context(context)
    assert not matched


def test_multiple_keyword_set_in_regexp_query():
    # - 여러개의 keyword_set 을 등록해서 사용할 수 있다.
    keyword_set_list = [
        ('keyword1', ['A', 'B', 'C']),
        ('keyword2', ['1', '2', '3'])
    ]
    environ = MatchEnvironment()
    for keyword_name, keyword_list in keyword_set_list:
        keyword_set = KeywordSet(keyword_name, keyword_list)
        environ.put_keyword_set(keyword_name, keyword_set)
    query = json_matcher.compile('field:/prefix@@{keyword2}postfix@@{keyword1}/')
    context = MatchContext({'field': 'prefix2postfixA'}, environ)
    matched = query.match_with_context(context)
    assert matched

    context = MatchContext({'field': 'prefixApostfix1'}, environ)
    matched = query.match_with_context(context)
    assert not matched


def test_some_regexp():
    query = "(html:/(<h1>다운로드<\\/h1>|<td class=gray_solid_file>파일명<\\\\/td><td class=gray_solid_file>용량<\\\\/td>)/)"
    query = '(html:/~/(<h1>다운로드<\\/h1>|<td class=gray_solid_file>파일명<\\\\/td><td class=gray_solid_file>용량<\\\\/td>)/~/)'
    print(query)
    json_matcher.compile(query)


def test_extract_match_keyword():
    # Simple Term
    assert json_matcher.match('field_name:"*안녕*"', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕\\//i', dict(field_name='여러분 안녕/하세요'))

    assert json_matcher.match('field_name:/(안녕|여러분|세상아)/i', dict(field_name='여러분 안녕/하세요'))


    # Regular Expression
    assert json_matcher.match('field_name:/a{1,3}b/i', dict(field_name='aab'))
    assert json_matcher.match('field_name:/\\d{2,3}/', dict(field_name='123'))
    assert json_matcher.match('field_name:/~/a{1,3}b/~/i', dict(field_name='aab'))
    assert json_matcher.match('field_name:/~/b/{1,3}/~/i', dict(field_name='b/'))

    # Keyword
    query = json_matcher.compile('field:/prefix@@{keyword}postfix/')
    environ = MatchEnvironment()
    environ.put_keyword_set('keyword', KeywordSet('keyword', ['A', 'B', 'C']))
    context = MatchContext({'field': 'prefixApostfix'}, environ)
    matched = query.match_with_context(context)
    assert matched


def test_counting_matcher():
    data = {
        'field_name': 'match1 match2 match3 match4 match5 match6'
    }

    assert json_matcher.match('field_name:COUNT(match)=6', data)
    assert json_matcher.match('field_name:COUNT(match)>=6', data)
    assert json_matcher.match('field_name:COUNT(match)>5', data)
    assert json_matcher.match('field_name:COUNT(match)<=6', data)
    assert json_matcher.match('field_name:COUNT(match)<7', data)

    assert not json_matcher.match('field_name:COUNT(match)<1', data)

    assert json_matcher.match('field_name:COUNT(/match\\d/)=6', data)
    assert json_matcher.match('field_name:COUNT(/match\\d/)>=6', data)
    assert json_matcher.match('field_name:COUNT(/match\\d/)>5', data)
    assert json_matcher.match('field_name:COUNT(/match\\d/)<=6', data)
    assert json_matcher.match('field_name:COUNT(/match\\d/)<7', data)

    assert not json_matcher.match('field_name:COUNT(/match\\d/)>1000', data)
    assert json_matcher.match('field_name:COUNT(/~/match[1]/~/)=1', data)

    environ = MatchEnvironment()
    environ.put_keyword_set('keyword', KeywordSet('keyword', ['match']))
    context = MatchContext(data, environ)

    assert json_matcher.compile('field_name:COUNT(@@{keyword})=6').match_with_context(context)
    assert json_matcher.compile('field_name:COUNT(@@{keyword})>=6').match_with_context(context)
    assert json_matcher.compile('field_name:COUNT(@@{keyword})>5').match_with_context(context)
    assert json_matcher.compile('field_name:COUNT(@@{keyword})<=6').match_with_context(context)
    assert json_matcher.compile('field_name:COUNT(@@{keyword})<7').match_with_context(context)

    data2 = {
        'field_name': ['match1', 'match2', 'match3', 'match4', 'match5', 'match6']
    }

    assert json_matcher.match('field_name:COUNT(match)=6', data2)
    assert json_matcher.match('field_name:COUNT(match)>=6', data2)
    assert json_matcher.match('field_name:COUNT(match)>5', data2)
    assert json_matcher.match('field_name:COUNT(match)<=6', data2)
    assert json_matcher.match('field_name:COUNT(match)<7', data2)

    data3 = {
        'field_name': '한글 테스트입니다. 잘 될까요? 한글 한글'
    }

    assert json_matcher.match('field_name:COUNT(한글)=3', data3)
    assert json_matcher.match('field_name:COUNT(한글 )=3', data3)
    assert json_matcher.match('field_name:COUNT("한글 ")=2', data3)
    assert json_matcher.match('field_name:COUNT("한글 테스트")=1', data3)

    assert not json_matcher.match('field_name:"COUNT(한글)=3"', data3)


def test_code_matcher():
    data = {
        'field_str': 'string value field',
        'field_int': 10,
        'field_zero': 0,
        'field_true': True,
        'field_false': False

    }
    environ = MatchEnvironment()
    environ.add_function('function_first_word', lambda s: s.split()[0])
    environ.add_function('function_true', lambda t: True)
    environ.add_function('function_false', lambda t: False)
    environ.add_function('function_identy', lambda t: bool(t))
    environ.add_function('function_name', lambda t: 'function')
    environ.add_function('function_2', lambda t, a1: a1)
    environ.add_function('function_3', lambda t, a1, a2: a2)
    context = MatchContext(data, environ)

    # 1 argument functions
    assert json_matcher.compile('field_str:!function_true').match_with_context(context)
    assert not json_matcher.compile('field_str:!function_false').match_with_context(context)
    assert json_matcher.compile('field_int:!function_identy').match_with_context(context)
    assert not json_matcher.compile('field_zero:!function_identy').match_with_context(context)
    assert json_matcher.compile('field_true:!function_identy').match_with_context(context)
    assert not json_matcher.compile('field_false:!function_identy').match_with_context(context)

    # 1 argument function with explicit argument
    assert json_matcher.compile('field_true:!function_identy(this)').match_with_context(context)
    assert not json_matcher.compile('field_false:!function_identy(this)').match_with_context(context)

    # 2 or more argument
    assert json_matcher.compile('field_true:!function_2(this,"argument1")').match_with_context(context)
    assert json_matcher.compile('field_true:!function_3(this,"argument1",True)').match_with_context(context)
    assert not json_matcher.compile('field_true:!function_3(this,"argument1",False)').match_with_context(context)

    # function with return value
    assert json_matcher.compile('field_false:!function_identy(this)==False').match_with_context(context)

    # with double quote with space
    assert json_matcher.compile('''field_true:!"function_2(this, 'argument1')"''').match_with_context(context)

    # using with _expr_
    assert json_matcher.compile('_expr_:"function_identy(field_true)"').match_with_context(context)
    assert json_matcher.compile('''_expr_:"function_first_word(field_str)=='string'"''').match_with_context(context)


def test_not_expression_groups():
    data = {'field_name': 'field_value'}
    query = 'NOT field_name:not_string'

    matcher = json_matcher.compile(query)
    r = matcher.match(data)
    l = r.groups()

    assert len(l) > 0


def test_bool_string():
    data = {'field_name': True}

    query = 'field_name:True'
    assert json_matcher.match(query, data)

    query_with_small_true = 'field_name:true'
    assert json_matcher.match(query_with_small_true, data)

    data = {'field_name': False}

    query = 'field_name:False'
    assert json_matcher.match(query, data)

    query_with_small_true = 'field_name:false'
    assert json_matcher.match(query_with_small_true, data)

    data = {'field_name': False}

    query = 'field_name:string_value'
    assert not json_matcher.match(query, data)

    query = 'field_name:0'
    assert not json_matcher.match(query, data)
