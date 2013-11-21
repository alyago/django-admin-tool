"""
Run it:
> python manage.py runscript emp_edit

Various admin functions...

Interesting queries:
*
SELECT name FROM employers_employer GROUP BY name HAVING COUNT(id) > 1
*
select url from emp_website where dedup is NULL group by url HAVING COUNT(id) > 1 order by url;
*
select COUNT(DISTINCT(employer_id)), url_subdomain, url_domain, url_suffix from emp_website where dedup is NULL group by url_subdomain, url_domain, url_suffix HAVING COUNT(DISTINCT(employer_id)) > 1 order by url_domain;

*
"""

# https://github.com/john-kurkowski/tldextract
# https://pypi.python.org/pypi/tldextract
import tldextract

from django.db.models import Q

from common_models_employers.models.employers import Employer
from common_models_employers.models.emp_data import EmpWebsite
from common_models_employers.models.emp_data import EmpWebprofile, EmpWebprofileType

def run():
    print u'Running emp_edit...'
    
    #dedup_names()
    #dedup_website()
    populate_rating()
    #populate_website_tld()
    #for code in ('in', 'gp', 'yt', 'ig', 'tm', 'pn', 'fl', ): populate_webprofile(code)
    #move_host_to_main()

from django.db import connections
def dedup_names():
    print "For names that appear more than once, set dedup to ticker"

    cursor = connections['employers'].cursor()
    cursor.execute("SELECT name FROM employers_employer GROUP BY name HAVING COUNT(id) > 1")
    #print cursor.description
    for row in cursor.fetchall():
        name = row[0]
        for e in Employer.objects.filter(name=name):
            ticker = e.emp_source_ids.get(source_type__code='bw').sid
            #e.dedup = bw.ticker
            print e.name, e.dedup, ticker
            #e.save()

def dedup_website():
    cursor = connections['employers'].cursor()
    cursor.execute("SELECT url from emp_website where dedup is NULL group by url HAVING COUNT(id) > 1")
    #print cursor.description
    for row in cursor.fetchall():
        url = row[0]
        for ew in EmpWebsite.objects.filter(url=url):
            ew.dedup = ew.employer.get_bw_id()
            print ew.url, ew.dedup
            ew.save()

from common_models_employers.models.sh_data import  ShRating
def populate_rating():
    q_filter = Q(sh_description__isnull=False) | Q(sh_snapshot_facts__isnull=False)\
             | Q(sh_display_name__isnull=False)
    es = Employer.objects.filter(q_filter).distinct()
    for e in es:
        print e
        r, created = ShRating.objects.get_or_create(employer=e, defaults={'rating': '0'})
    print es.count()

from urlparse import urlparse
from django import forms
def populate_webprofile(code):
    furl = forms.URLField()
    for wp in EmpWebprofile.objects.filter(webprofile_type__code=code):
        try:
            url =  furl.clean(wp.url)
        except Exception as e:
            print "-- FAILED! --> ", wp.url, " | ", wp.employer, " | ", e
        else:
            wp.url = url
            path = urlparse(url).path
            if code == 'tw':
                description = path.split('/')[1]
                wp.description = description
                wp.url = "http://www.twitter.com/" + description
            elif code == 'fb':
                wp.url = "https://www.facebook.com" + path
                if not path.startswith('/pages/'):
                    wp.description = path.split('/')[1]
            wp.save()
            print wp, "|", wp.description, " | ", wp.employer
            
    return
    
def populate_website_tld():
    
    for emp_website in EmpWebsite.objects.all():
        url = emp_website.url
        ext = tldextract.extract(url)
        emp_website.url_subdomain = ext.subdomain if ext.subdomain != '' else None
        emp_website.url_domain = ext.domain
        emp_website.url_suffix = '-' if ext.suffix == '' else ext.suffix
        
        emp_website.txt = '.'.join(filter(None,
                                        [emp_website.url_subdomain,
                                         emp_website.url_domain,
                                         emp_website.url_suffix]))
        
        emp_website.save()


from common_models_employers.models.employers import Host
def move_host_to_main():
    
    for h in Host.objects.all():
        print h.id, h.employer, h.url, h.txt
        w, created = EmpWebsite.objects.get_or_create(url=h.url, employer=h.employer)
        w.description = h.txt
        w.save()
        w.mark_as_main()