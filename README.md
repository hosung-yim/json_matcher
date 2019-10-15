# json_matcher

Match json object with query like elasticsearch/lucene query.

examples (jrep)

    # cat a.txt
    { "foo": "bar", "bar": "foo" }
    # jrep "foo:bar" /tmp/a.txt
    { "foo": "bar", "bar": "foo" }

examples (json\_matcher)

    >>> import json_matcher
    >>> matcher = json_matcher.compile('foo:bar bar:foo')
    >>> j = dict(foo='bar', bar='foo')
    >>> m = matcher.match(j)
    >>> m.groups()
    [('foo', 'bar'), ('bar', 'foo')]

    >>> matcher = json_matcher.compile('foo:>10 bar:foo')
    >>> j = dict(foo=11, bar='foo')
    >>> matcher.match(j).groups()
    [('foo', 11), ('bar', 'foo')]
    >>> j = dict(foo=9, bar='foo')
    >>> matcher.match(j)
    >>> m = matcher.match(j)
    >>> print(m)
    None

    >>> json_matcher.match('foo:[10 TO 20] AND bar:foo', dict(foo=11, bar='foo')).groups()
    [('foo', 11), ('bar', 'foo')]

    >>> nested = dict(A=dict(B=dict(C='Hello World')))
    >>> json_matcher.match('A.B.C:"Hello World"', nested).groups()
    [('A.B.C', 'Hello World')]

    
- match text or number with ```field_name:value```
- match regular expression with ```field_name:/regular expression/```
- match range with ```field_name:[10 TO 20]```, ```field_name:[10 TO 20}``` (exclusive 20)
- match range(open range) with ```field_name:>20``` (like elasticsearch not lucene)
- match field existence with ```_exists_:field_name```
- match expression with ```_expression:"python expression"```
    
TODO:
 - multiple match with high performace (with Ahocorasik and RE2???)


