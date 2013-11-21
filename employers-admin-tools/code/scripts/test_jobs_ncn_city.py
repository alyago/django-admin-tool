"""
Run it:
> python manage.py runscript test_jobs_ncn_city


"""
import json
import time
from urllib import urlencode, quote_plus
from collections import namedtuple, OrderedDict
import requests


def run():
    print u'Testing LuceneSearchServlet...'
    top_cities_for_company_raw(company='Adobe Systems', results=20)


def __request_top_cities(company, results):
    now = time.localtime()
    timestamp = time.strftime('_T:%H:%M_W:{week}_D:%m_%d_%Y', now).format(
        week=(now.tm_mday - 1) // 7 + 1)
    exclusions = "A:1002_O:internal.simplyhired.com_P:jobs_C:list_N:unk_S:reg%s" % timestamp
    query = json.dumps({
        "searchSpecs": {
            "exclusions": exclusions,
            "filters": {"companyFilter": company,
                        "global":"NOT robotId:21273 NOT robotId:25038 NOT robotId:5099 NOT robotId:24405 NOT robotId:5320 NOT robotId:8686 NOT robotId:5296"
                        },
            "enable_facet_counts": True
        },
        "resultOrganizerSpecs": {
            "num_results": results,
        },
        "country": "us",
        "query":"cityState:\"San Jose, CA\"",
    })
    
    encoded = urlencode({'jsonStr': query})
    url = 'http://balance-search-vip.ksjc.sh.colo:11010/simplyhired/LuceneSearchServlet?%s' % encoded
    return requests.get(url)


def top_cities_for_company_raw(company, results=10):
    """Returns raw json for debugging"""
    response = __request_top_cities(company, results)
    
    print json.dumps(json.loads(response.content), sort_keys=True, indent=4)
    #return response.content
