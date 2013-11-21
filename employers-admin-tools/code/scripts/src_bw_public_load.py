"""
Run it:
> python manage.py runscript src_bw_public_load


Interesting queries:
*
SELECT name from src_bw_public group by name HAVING COUNT(id) > 1
*
"""
import os
import json
import re
from datetime import datetime

# https://github.com/john-kurkowski/tldextract
# https://pypi.python.org/pypi/tldextract
import tldextract

from django.db import IntegrityError

from common_models_employers.models.src_data import SrcBwPublic

DATA_ROOT = '/home/oleg/test/scrapy_test/tutorial/data'
DATA_TYPE = 'private'
DATA_NAME = 'bw-' + DATA_TYPE
REGIONS = ['US', 'Americas', 'Europe', 'Asia', 'MidEastAfr']
LETTER_INS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
              'A', 'B', 'C', 'D', 'E',
              'F', 'G', 'H', 'I', 'J',
              'K', 'L', 'M', 'N', 'O',
              'P', 'Q', 'R', 'S', 'T',
              'U', 'V', 'W', 'X', 'Y', 'Z']

REGIONS = ['Europe']
LETTER_INS = ['0']

def run():
    print u'Loading ', DATA_NAME, " ..."
    
    for region in REGIONS:
        for letterIn in LETTER_INS:
            
            data_path = os.path.join(DATA_ROOT, DATA_NAME, region, letterIn)
            data_file = os.path.join(data_path,
                                     '-'.join([DATA_NAME, region, letterIn]) + '.json')
            
            if not os.path.isfile(data_file):
                print "? ", data_file
                continue
            
            print region, letterIn
            
            with open(data_file, 'rb') as f:
                for line in f:
                    data_json = json.loads(line)
                    try:
                        load_one_company(data_json)
                    except Exception as e:
                        print "-- HMM... ????? --> some mysterious error, skipping... ", e
                        print data_file
                        print json.dumps(data_json, sort_keys=True, indent=4, separators=(',', ': '))
                f.closed

    
def load_one_company(data_json):
    """
    Update only non null (non '') values!
    If web crawl crashed and only partial data was scraped,
    we don't want null values overwrite non-nulls in DB.
    On the other hand, if some value scraped from web is non-null,
    it is more current than in DB, so DB must be updated
    """
    #print json.dumps(data_json, sort_keys=True, indent=4, separators=(',', ': '))
    #return

    # unique identity: name dedup ticker
    name = data_json['name']
    dedup = ''
    ticker = data_json['ticker']
    
    # dedup company name
    if False:
        if ticker in ('CMYF:US',
                      'CNAF:US',
                      'FBSI:US',
                      'FBP:US',
                      'MLLS:US',
                      'PSBH:US',
                      'PLZB:US',
                      '7605:JP',
                      '7452:JP',
                      '5987:JP',
                      '1885:JP',
                      '2656:JP',
                      'RCFL:IN'
                      ):
            dedup = ticker
    
    # if lookup_page is missing - it should be 1
    if data_json['lookup_page'] == '':
        data_json['lookup_page'] = '1'
    
    cd = {}
        
    # copy only non nulls:
    for k in ['capital_iq_industry',
              'country',
              'description_short',
              'employees_date',
              'employees_num',
              'exchange',
              'hq_address',
              'industry',
              'industry_code',
              'letter_in',
              'lookup_page',
              'lookup_row',
              'phone',
              'region',
              'sector',
              'sector_code',
              'web_txt',
              'web_url',
              'year_founded']:
        if data_json.get(k, '') != '':
            cd[k] = data_json[k] 
    
    # modify for db types
    if cd.has_key('employees_date'):
        cd['employees_date'] = datetime.strptime(cd['employees_date'], "%m/%d/%y")
        
    if cd.has_key('employees_num'):
        cd['employees_num'] = cd['employees_num'].replace(',', '').replace('.', '')
    
    # split web_url into suffix, domain and subdomain
    if cd.has_key('web_url'):
        # cleaning...
        web_url = cd['web_url'].replace(',Inc.', '.com')\
            .strip().replace(' ', '').replace(',', '').replace(u"\u00ad", '')\
            .replace('http:\\\\', 'http://').replace('http://Https://', 'http://')\
            .replace('http:////', 'http://').replace('http:///', 'http://')\
            .replace('http://http://', 'http://').replace('http://p://', 'http://')\
            .replace('.com\\', '.com/')\
            .replace('%2f', '/').replace('\\www.', 'www')
        
        web_url = re.sub('\.n$', '.nl', web_url)
        web_url = re.sub('\.z$', '.za', web_url)
        web_url = re.sub('\.t$', '.tr', web_url)
        web_url = re.sub('\.j$', '.jp', web_url)
        web_url = re.sub('\.f$', '.fi', web_url)
        web_url = re.sub('\.e$', '.eu', web_url)
        web_url = re.sub('\.p$', '.pl', web_url)
        web_url = re.sub('\.b$', '.br', web_url)
        web_url = re.sub('-fr$', '.fr', web_url)
        web_url = re.sub('\.coml$', '.com', web_url)
        web_url = re.sub('\.co\.au$', '.com.au', web_url)
        web_url = re.sub('\.au\.com$', '.com.au', web_url)
        web_url = re.sub('\.tu$', '.ru', web_url)
        
        cd['web_url'] = web_url
        special_case = False
        suffix = ''
        for su in ['co.yu', 'cg.yu', 'org.yu', 'telekom.yu',
                   'tp', 'wordpress.com', 'webs.com',
                   'webnode.com', 'myshopify.com', 'napawebtools.com']:
            if web_url.endswith('.'+su):
                special_case = True
                suffix = su
                web_url = web_url.replace('.'+su, '.com')
        ext = tldextract.extract(web_url)
        cd['web_url_subdomain'] = ext.subdomain if ext.subdomain != '' else None
        cd['web_url_domain'] = ext.domain
        if ext.suffix == '':
            cd['web_url_suffix'] = '-'
        elif special_case:
            cd['web_url_suffix'] = suffix
        else:
            cd['web_url_suffix'] = ext.suffix
        
        if cd['web_url'].endswith(cd['web_url_suffix']):
            cd['web_url'] += '/'
            
    # set is_public, for public split ticker into stock ticker and stock exchange
    if DATA_TYPE == 'public':
        cd['ticker_t'], cd['ticker_e'] = ticker.split(':')
        cd['is_public'] = True
    elif DATA_TYPE == 'private':
        cd['is_public'] = False
        
    #print cd

    # now add to database
    bwobs = None
    if DATA_TYPE == 'private':
        bwobs = SrcBwPublic.objects
    elif DATA_TYPE == 'public':
        bwobs = SrcBwPublic.objects
    
    # cleaner way...
    if bwobs.filter(ticker=ticker).exists():
        # bw exists, just update:
        bw = bwobs.get(ticker=ticker)
        if bw.name != name:
            print "-- NAME HAS CHANGED --> for ticker %s from %s to %s" % (ticker, bw.name, name)
            # update name
            try:
                bw.name = name
                bw.save()
            except IntegrityError as ie:
                # dedup the name
                print "... AND NEED TO DEDUP IT"
                bw.dedup = ticker
                bw.save()
            except Exception as e:
                print "-- HMM... ?? --> something's really wrong, skipping...", e
                return
        # update
        [setattr(bw, key, value) for (key, value) in cd.items()]
        bw.save()
    else:
        # create new
        if bwobs.filter(name=name).exists():
            # another company with the same name already exists
            # dedup it...
            dedup = ticker
            
        try:
            bw, created = bwobs.get_or_create(name=name, dedup=dedup, ticker=ticker, defaults=cd)
        except Exception as e:
            print "-- HMM... ? --> could not create, skipping: %s - %s" % (name, ticker), e
            print cd
            return
        
    return

    