"""
Run it:
> python manage.py runscript jobs_company_edit

DB stuff:
==
INSERT INTO
jobs_company (normalized_company_name,company_hash,parent,source_type,type,domain,url,page_title,validate,ppr_validated)
SELECT        normalized_company_name,company_hash,parent,source_type,type,domain,url,page_title,validate,ppr_validated
FROM Companies;


Interesting queries:
*
select count(domain_domain), domain_domain, domain_suffix
from jobs_company
group by domain_domain, domain_suffix
order by count(domain_domain) desc LIMIT 200;
*
select count(domain_domain)
from jobs_company
group by domain_domain, domain_suffix;
*
select count(canonical_company_name), canonical_company_name
from jobs_company
group by canonical_company_name
order by count(canonical_company_name) desc LIMIT 200;
*
==
"""
from django.utils.text import slugify
from django.db.models import F
from django.db.models import Q
from django.db.models import Max
from django.db.models import Min

# https://github.com/john-kurkowski/tldextract
# https://pypi.python.org/pypi/tldextract
import tldextract

#from common_models_employers.models.employers import Employer
from common_models_employers.models.sh_jobs import JobsCompany
from common_models_employers.models.employers import Employer
from common_models_employers.models.emp_data import EmpWebsite

def run():
    print u'Here we go!'
    #employer_list = Employer.objects.order_by('name')[:25]
    #print employer_list
    
    #JobsCompany.objects.all().update(canonical_company_name=slugify(F('normalized_company_name')))
    
    #for jc in JobsCompany.objects.filter(Q(normalized_company_name__icontains='adobe') |
    #                                     Q(domain__icontains='adobe')):

    populate_employer()
    #populate_canonical()
    #populate_domain_tld()
    #populate_canonical_underscore()
    #populate_canonical_dash()
    

def populate_employer():
    #es = Employer.objects.filter(emp_websites__url_domain='lion',
    #                                  emp_websites__url_suffix='com.mys').distinct()
    #print es
    #return
    
    q_filter = Q(done=0, domain_domain__isnull=False)
    count = JobsCompany.objects.filter(q_filter).count()
    print count
    if count == 0: return
    
    #min_max = JobsCompany.objects.\
    #            filter(q_filter).\
    #            aggregate(i_min=Min('pk'), i_max=Max('pk'))
    #i_min = min_max['i_min']
    #i_max = min_max['i_max']
    #print "min: ", i_min, " | max: ", i_max
    
    # while loop with blocks of 1,000 ncns
    #for i in range(i_min, i_max+1):
    while JobsCompany.objects.filter(q_filter).exists():
        #jcs = JobsCompany.objects.filter(q_filter, pk=i)
        #if jcs.exists():
        for jc in JobsCompany.objects.filter(q_filter)[:1000]:
            #jc = jcs.get()
            domain = jc.domain_domain
            suffix = jc.domain_suffix
            
            es = Employer.objects.\
                    filter(emp_websites__url_domain=domain,
                           emp_websites__url_suffix=suffix).\
                    distinct()
            if not es.exists():
                jc.done=1
                jc.save()
            elif len(es) == 1:
                jc.employer = es.get()
                jc.done=1
                jc.save()
            else: #len(es) > 1: # multiple employers matched...
                # TO DO: check which website is "main"
                # TO DO: print domain.suffix
                print jc
                print es
                jc.done = 1
                jc.save()
            
        
    
def populate_domain_tld():
    min_max = JobsCompany.objects.\
                filter(domain_domain__isnull=True, domain__isnull=False).\
                aggregate(i_min=Min('pk'), i_max=Max('pk'))
    i_min = min_max['i_min']
    i_max = min_max['i_max']
    print "min: ", i_min, " | max: ", i_max, " | total: ", i_max+1-i_min
    count = 0
    
    #q_filter = Q(normalized_company_name__icontains='ricoh') | Q(domain__icontains='ricoh')
    #for jc in JobsCompany.objects.filter(q_filter):
    #    ext = tldextract.extract(jc.domain)
    #    
    #    print ext
    #    
    #    jc.domain_subdomain = ext.subdomain
    #    jc.domain_domain = ext.domain
    #    jc.domain_suffix = ext.suffix
    #    jc.save()
    #    count += 1
    
    for i in range(i_min, i_max+1):
        try:
            jc = JobsCompany.objects.\
                filter(domain_domain__isnull=True, domain__isnull=False).\
                only('domain', 'domain_subdomain', 'domain_domain', 'domain_suffix').\
                get(pk=i)
            ext = tldextract.extract(jc.domain)
            jc.domain_subdomain = ext.subdomain
            jc.domain_domain = ext.domain
            jc.domain_suffix = '-' if ext.suffix == '' else ext.suffix
            jc.save()
            count += 1
        except JobsCompany.DoesNotExist:
            pass
        except TypeError:
            print "TypeError: ", jc.domain
        except UnicodeEncodeError:
            print "UnicodeEncodeError: ", jc.domain
        
    print "total populated: ", count
        
   
def populate_canonical():
    min_max = JobsCompany.objects.filter(canonical_company_name__isnull=True).aggregate(i_min=Min('pk'), i_max=Max('pk'))
    i_min = min_max['i_min']
    i_max = min_max['i_max']
    print "min: ", i_min, " | max: ", i_max, " | total: ", i_max+1-i_min
    count = 0
    
    for i in range(i_min, i_max+1):
        try:
            jc = JobsCompany.objects.only('normalized_company_name', 'canonical_company_name').get(pk=i)
            ncn = jc.normalized_company_name
            jc.canonical_company_name = slugify(ncn.replace('_', ' ')).strip('-')
            jc.save()
            count += 1
        except JobsCompany.DoesNotExist:
            pass
        
    print "total populated: ", count
    
def populate_canonical_dash():
    q_filter = Q(canonical_company_name__startswith='-') | Q(canonical_company_name__endswith='-')
    print JobsCompany.objects.filter(q_filter).count()
    
    for jc in JobsCompany.objects.filter(q_filter):
        ncn = jc.normalized_company_name
        jc.canonical_company_name = slugify(ncn.replace('_', ' ')).strip('-')
        jc.save()
    
def populate_canonical_underscore():
    q_filter = Q(normalized_company_name__icontains='_')
    for jc in JobsCompany.objects.filter(q_filter):
        ncn = jc.normalized_company_name
        jc.canonical_company_name = slugify(ncn.replace('_', ' ')).strip('-')
        jc.save()
        
