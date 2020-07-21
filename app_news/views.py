# Create your views here.

import json

from math import ceil
from django.http import HttpResponse

from libs import myLog
from tools.news_tool import SqliteDb
from tools.thesaurus import sqlFilterTool


def page_num(request):
    type = request.POST.get('type')          # str
    limit = request.POST.get('limit')        # int

    if not type or not limit:
        return HttpResponse(b'FORCE EXIT', status=403)

    form = {}
    limit = int(limit)
    eqWhe = {} if type == 'all' else {'type': type}

    with SqliteDb() as db:
        code, res = db.base_r(sel='count("tittle")', eqWhe=eqWhe)
        if code:
            form['pageNum'] = ceil(res[0][0] / limit)
        else:
            form['pageNum'] = res

        return HttpResponse(json.dumps(form).encode())


def page(request):
    body = json.loads(request.body)
    type = body.get('type')          # str
    limit = body.get('limit')        # int
    pageNum = body.get('pageNum')    # int

    if not type or not limit or not pageNum:
        return HttpResponse(b'FORCE EXIT', status=403)

    if not isinstance(limit, int) or not isinstance(pageNum, int):
        myLog.warning('SQL注入，%s' % ((limit, pageNum), ))
        return HttpResponse(b"SQL INJECTION", status=403)

    form = {'data': []}
    limit = int(limit)
    pageNum = int(pageNum)
    _min = limit * (pageNum - 1)
    limit = 'order by `time` limit %s,%s' % (_min, pageNum)

    with SqliteDb() as db:
        eqWhe = {'type': type}
        code, res = db.base_r(eqWhe=eqWhe, suffix=limit)
        if code:
            for i in res:
                tittle, releaseTime, abstract, url, *purls = i
                form['data'].append([tittle, releaseTime, abstract, url, purls])
        else:
            form['data'].append(str(res))
        return HttpResponse(json.dumps(form).encode())
