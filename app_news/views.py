from django.http import HttpResponse


# Create your views here.


import json
from tools.news_tool import SqliteDb


def page_num(request):
    type = request.GET.get('type')
    limit = request.GET.get('limit')

    if not type or not limit:
        return HttpResponse(b'NOT EXIST', status=403)

    eqWhe = {'type': type} if type != 'all' else {}
    with SqliteDb() as db:
        code, res = db.base_r(sel='count("tittle")', eqWhe=eqWhe)
        if code:
            form = {
                'pageNum': res[0][0]
            }
            return HttpResponse(json.dumps(form).encode())

        return HttpResponse(res.encode())



def page(request):
    type = request.GET.get('type')
    limit = request.GET.get('limit')
    pageNum = request.GET.get('pageNum')

    if not type or not limit or not pageNum:
        return HttpResponse(b'NOT EXIST', status=403)

    _min = limit * (int(pageNum) - 1)
    limit = 'order by `time` limit %s,%s' % (_min, pageNum)

    with SqliteDb() as db:
        eqWhe = {'type': type}
        code, res = db.base_r(eqWhe=eqWhe, suffix=limit)
        if code:
            form = {'data': []}
            for i in res:
                tittle, releaseTime, abstract, url, *purls = i
                form['data'].append([tittle, releaseTime, abstract, url, purls])

                return HttpResponse(json.dumps(form).encode())

        return HttpResponse(res.encode())