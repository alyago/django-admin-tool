"""
This script requires django-extensions in order to run. To install, activate
your employers virtual environment and run:

    pip install django-extensions

Then, add the following to your INSTALLED_APPS in settings.py:

    'django_extensions'

Afterwards, you can run the script via:

    > python manage.py runscript import_csv_gdoc


> scp CompanyPageDatabase-20131111.csv oleg@xen-oleg-1.ksjc.sh.colo:/home/oleg/tmpdata/company_page_database/.
"""
import os
import unicodecsv
import urlparse
from django.db import models
from django import forms

# https://github.com/john-kurkowski/tldextract
# https://pypi.python.org/pypi/tldextract
import tldextract

from common_models_employers.models.employers import Employer
from common_models_employers.models.src_data import SrcBwPublic
from common_models_employers.models.emp_data import EmpSourceId, EmpWebsite, EmpWebsiteType,\
                                                    EmpWebprofileType, EmpWebprofile
from common_models_employers.models.sh_data import ShDisplayName, ShDescription,\
                                                    ShSnapshotFactType, ShSnapshotFact
from common_models_employers.models.src_data import SrcSourceType
st_bw = SrcSourceType.objects.get(code='bw')

DATA_ROOT = '/home/oleg/tmpdata/company_page_database/'
DATA_FILE_NAME = 'CompanyPageDatabase-20131111.csv'
cols = (
    ('name', u"Company"),
    ('link', u"Emp Link"),
    ('ticker', u"Stock Ticker Symbol"),
    ('employees', u"# of Employees"),
    #('revenue', u"Annual Revenue"),
    ('founded', u"Year Founded (Year only)"),
    ('founders', u"Founders (One name per line)"),
    ('headquarters', u"Headquarters Location (Line1=Street)(Line2=City State Zip)"),
    ('products', u"Products List (one per line)"),
    ('services', u"Services List (one per line)"),
    ('funfact', u"Fun Fact"),
    ('url', u"Website Address URL"),
    ('facebook', u"Facebook Page"),
    ('twitter', u"Twitter Handle"),
    ('linkedin', u"LinkedIN page"),
    ('youtube', u"YouTube Channel"),
    ('instagram', u"Instagram Profile"),
    ('tumblr', u"Tumblr Page"),
    ('pinterest', u"Pinterest Page"),
    ('flickr', u"Flickr Page"),
    ('desc1', u"Description 1"),
    ('desc2', u"Description 2"),
    ('desc3', u"Description 3"),
    ('desc4', u"Description 4"),
)

pars = {'desc1': '1',
        'desc2': '2',
        'desc3': '3',
        'desc4': '4'
        }

sftypes = {'ticker': 1,
           'employees': 2,
           'founded': 4,
           'founders': 5,
           'headquarters': 6,
           'products': 7,
           'services': 8,
           'funfact': 9
           }

wptypes = {'facebook': "fb",
            'twitter': "tw",
            'linkedin': "in",
            'youtube': "yt",
            'instagram': "ig",
            'tumblr': "tm",
            'pinterest': "pn",
            'flickr': "fl"
            }

def run():
    print u'Importing from csv google doc...'
    
    data_file = DATA_ROOT + DATA_FILE_NAME
    
    with open(data_file, 'rb') as f:
        csv = unicodecsv.DictReader(f)
        
        for row in csv:
            try:
                import_one_company(row)
            except Exception as e:
                print "-- HMM... ????? --> some mysterious error, skipping... ", e
                print row
                print "========\n"
            
            #return


def import_one_company(row):
    
    cd = {}
    for k, c in cols:
        cd[k] = row[c]
    
    #print row   
    #for k, c in cols: print k, " = ", cd[k]
    #print "========\n"
            
    name = cd['name']
    link = cd['link']
    ticker = cd['ticker']
    url = cd['url']
    ext = tldextract.extract(url)
    url_subdomain = ext.subdomain if ext.subdomain != '' else None
    url_domain = ext.domain
    url_suffix = ext.suffix
    url_txt = '.'.join(filter(None,
                            [url_subdomain,
                             url_domain,
                             url_suffix]))
    furl = forms.URLField()
    url_formatted = furl.clean(url)
    
    matched = False
    ef = None
    
    if link != '':
        print 'link = ', link
        ef = Employer.objects.filter(links__link = link)
        matched = True
    else:
        es = Employer.objects.\
                        filter(emp_websites__url_domain=url_domain,
                               emp_websites__url_suffix=url_suffix).\
                        distinct()
        
        if len(es) == 1:
            matched = True
            ef = es
            #print "MATCH BY URL!"
            #print es.get(), " | ", es.get().get_bw_id()
        elif len(es) > 1: # multiple employers matched...
            print es
            esn = es.filter(name=name)
            if len(esn) == 1:
                matched = True
                ef = esn
                #print "MATCH BY URL + NAME!"
                #print esn.get(), " | ", esn.get().get_bw_id()
            elif len(esn) > 1: # should never happen!
                print esn
            else:
                print "!!!"
        else:
            #print "???"
            esn = Employer.objects.filter(name__icontains = name)
            
            if len(esn) == 1:
                matched = True
                ef = esn
                #print "MATCH BY NAME!"
                #print esn.get(), " | ", esn.get().get_bw_id()
            elif len(esn) > 1:
                print "by name: ", esn
            
            if not matched and ticker != '':
                ex, t = ticker.split(':')
                t = t.strip()
                bw = SrcBwPublic.objects.filter(ticker_t = t)
                print "by ticker ", ticker, " : ", bw
    
    
    if not matched:
        print "++++++++"
        print name, " | ", ticker
        print url
        print "\n"

    if matched: # False: #
        employer = ef.get()
        print "========"
        print name, " | ", employer
        print ticker, " | ", employer.get_bw_id()
        print url
        
        #
        # now update db
        #
        
        # display name
        if not employer.sh_display_name.exists():
            dn = ShDisplayName.objects.create(employer=employer, name=name)
            print "Added display name: ", dn
        
        # descriptions
        print "Descriptions updated:"
        for k, t in pars.items():
            if cd[k] != '':
                paragraph = cd[k]
                des, created = ShDescription.objects.\
                               get_or_create(employer=employer,
                                            order=t,
                                            defaults={'paragraph': paragraph})
                if not created:
                    des.paragraph = paragraph
                    des.save()
                    
                print des.order, " ", des.paragraph[:47], " ..."
        
        # snapshot facts
        print "Snapshot Facts Updated: "
        for k, t in sftypes.items():
            if cd[k] != '':
                txt = cd[k].replace('\n', '<br/>\n')
                sft = ShSnapshotFactType.objects.get(order=t)
                sf, created = ShSnapshotFact.objects.get_or_create(employer=employer,
                                                     snapshot_fact_type=sft,
                                                     defaults={'txt': txt})
                if not created:
                    sf.txt = txt
                    sf.save()
                
                print sf.snapshot_fact_type, " ", sf.txt
        
        # website
        # if this website url is already in db for this employer - do nothing
        if not EmpWebsite.objects.filter(employer=employer, url=url_formatted).exists():
            #and not EmpWebsite.objects.filter(employer=employer, txt=txt).exists()):
            dedup = ''
            
            if EmpWebsite.objects.filter(url=url_formatted).exists():
                # this same url exists at another employer - we need to dedup...
                dedup = employer.get_bw_id()
            
            
            print "Adding website: ", url_formatted, " | ", dedup
            w = EmpWebsite.objects.create(employer=employer, url=url_formatted, dedup=dedup,
                                          txt=url_txt, url_subdomain=url_subdomain,
                                          url_domain=url_domain, url_suffix=url_suffix)
            #w.save()
            print "Added: ", w
        
        # webprofiles
        for k, t in wptypes.items():
            if cd[k] != '':
                url=cd[k]
                if t == 'tw' and url.startswith('@'):
                    url = 'https://twitter.com/' + url.strip('@')
                    
                webprofile_type = EmpWebprofileType.objects.get(code=t)
                EmpWebprofile.objects.get_or_create(url=url,
                                                    webprofile_type=webprofile_type,
                                                    employer=employer)
        
        print "\n"
        