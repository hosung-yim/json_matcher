#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import sys
import json

import json_matcher


def test_compile_text_term():
    assert json_matcher.compile('field_name:안녕')
    assert json_matcher.match('field_name:안녕', dict(field_name='여러분 안녕하세요'))

    assert json_matcher.match('field_name:"안녕"', dict(field_name='여러분 안녕하세요'))
    assert json_matcher.match('field_name:/안녕/i', dict(field_name='여러분 안녕하세요'))

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


def test_compile_multiple_term():
    assert json_matcher.compile('field_name:(안녕 세상아 반갑다)')
    assert json_matcher.match('field_name:(안녕 "세상아" 반갑다)', dict(field_name='안녕 세상아 반갑다. 진짜로'))
    assert not json_matcher.match('field_name:(안녕 "세상아" a{1,3}b)', dict(field_name='ab'))
    assert json_matcher.match('field_name:(안녕 "세상아" /a{1,3}b/)', dict(field_name='ab'))


def test_compile_nested_par():
    assert json_matcher.compile('((A:안녕 && B:세상아) C:반갑다)')

    assert json_matcher.compile('((A:안녕 AND B:세상아) AND C:반갑다)')
    assert json_matcher.match('((A:안녕 AND B:세상아) AND C:반갑다)', dict(A='안녕',B='세상아',C='반갑다'))
    assert not json_matcher.match('((A:안녕 AND B:세상아) AND C:반갑다)', dict(A='안녕',B='세상아'))


def test_default_and():
    assert json_matcher.match('A:안녕 B:세상아 C:반갑다', dict(A='안녕',B='세상아',C='반갑다'))
    assert not json_matcher.match('A:안녕 B:세상아 C:반갑다', dict(A='Y',B='세상아',C='반갑다'))


def test_with_list():
    assert json_matcher.match('A:안녕', dict(A=['안녕', '세상아', '반갑다']))
    assert json_matcher.match('A:안녕', dict(A=dict(B=['안녕', '세상아', '반갑다'])))
    assert json_matcher.match('A:안녕', dict(A=dict(A_=dict(B=['안녕', '세상아', '반갑다']))))

    assert json_matcher.match('field_name:[10 TO 30]', dict(field_name=[1,2,3,4,5,20]))
    assert not json_matcher.match('field_name:[10 TO 30]', dict(field_name=[1,2,3,4,5,6]))
    assert json_matcher.match('field_name:<10', dict(field_name=[11, 20, 30, 5, 30]))
    assert not json_matcher.match('field_name:<10', dict(field_name=[11, 20, 30]))
    assert json_matcher.match('field_name:(안녕 "세상아" 반갑다)', dict(field_name=dict(B=['이건아님', '안녕 세상아 반갑다. 진짜로'])))
    assert not json_matcher.match('field_name:(안녕 "세상아" 반갑다)', dict(field_name=['A', 'B', 'C']))


def test_exists():
    assert json_matcher.match('_exists_:A', dict(A='안녕'))
    assert json_matcher.match('_exists_:A', dict(A=None))
    assert not json_matcher.match('_exists_:A', dict(B='안녕'))


def test_expression():
    assert json_matcher.match('_expr_:"A+B>10"', dict(A=10,B=20))
    assert json_matcher.match('_expr_:"A.B+B.C>10"', dict(A=dict(B=10),B=dict(C=20)))


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
