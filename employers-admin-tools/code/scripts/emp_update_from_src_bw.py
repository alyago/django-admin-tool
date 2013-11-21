"""
Run it:
> python manage.py runscript emp_update_from_src_bw

Interesting queries:
*
select url from emp_website where dedup is NULL group by url order by count(id) desc LIMIT 121;
*
"""
from django.utils.text import slugify
from django.db import IntegrityError
from django.db.models import Q

from common_models_employers.models.src_data import SrcSourceType, SrcBwPublic
from common_models_employers.models.emp_data import EmpSourceId, EmpWebsite, EmpWebsiteType,\
                                                    EmpWebprofileType, EmpWebprofile
from common_models_employers.models.employers import Employer
from common_models_employers.models.sh_data import ShLink

ST_BW = SrcSourceType.objects.get(code='bw') # for public companies
ST_BP = SrcSourceType.objects.get(code='bp') # for private companies
WP_BW = EmpWebprofileType.objects.get(code='bw')
WT_WO = EmpWebsiteType.objects.get(code='wo')

REGIONS = ['US', 'Americas', 'Europe', 'Asia', 'MidEastAfr']
LETTER_INS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
              'A',   'B',   'C',
              'D', 'E',
              'F', 'G',
              'H', 'I',
              'J', 'K', 'L',
              'M',
              'N', 'O',
              'P',
              'Q', 'R',
              'S',   'T',
              'U', 'V',
              'W', 'X', 'Y', 'Z']

REGIONS = ['Americas']
LETTER_INS = ['T',
              'U', 'V',
              'W', 'X', 'Y', 'Z']
DEBUG = False

def run():
    print u'Running emp_update_from_src_bw...'
    
    is_public = False
    print u'is_public = ', is_public, '\n'
    
    #q_filter = Q(ticker='47113672')
    #bw = SrcBwPublic.objects.filter(q_filter).get()
    #print bw, "updating..."
    #update_one_employer(bw)
    #return
    
    for region in REGIONS:
        for letterIn in LETTER_INS:
            
            print region, letterIn
            
            
            q_filter = Q(region=region, letter_in=letterIn, is_public=is_public)
            for bw in SrcBwPublic.objects.filter(q_filter):
                try:
                    update_one_employer(bw)
                except Exception as e:
                    print "-- HMM... ????? --> some mysterious error, skipping... ", e
                    print bw
                    
    print '\n'

def update_one_employer(bw):
    if DEBUG: print bw
    #return

    esid = None
    e_created = False
    try:
        esid = EmpSourceId.objects.get(source_type=ST_BW, sid=bw.ticker)
    except EmpSourceId.DoesNotExist:
        emp, e_created = Employer.objects.get_or_create(name=bw.name, dedup=bw.dedup)
        esid = EmpSourceId.objects.create(employer=emp, source_type=ST_BW, sid=bw.ticker)
    
    # now esid exists
    employer = esid.employer
    if DEBUG: print esid, employer
    
    #
    # add or update website
    #
    if bw.web_url is not None:
        w_created = False
        
        # if this website url is already in db for this employer - do nothing
        if not EmpWebsite.objects.filter(employer=employer, url=bw.web_url).exists():
            w_dedup = ''
            if EmpWebsite.objects.filter(url=bw.web_url).exists():
                # this same url exists at another employer - we need to dedup...
                w_dedup = bw.ticker
            try:
                w = EmpWebsite.objects.create(employer=employer, url=bw.web_url, dedup=w_dedup)
            except IntegrityError as ie:
                print "-- WE SHOULD NEVER GET THERE! --> skipping... employer: %s | bw: %s" \
                    % (employer, bw), ie
            except Exception as e:
                print "-- HMM... ?? --> something's really wrong, skipping... employer: %s | bw: %s" \
                    % (employer, bw), e
            else:
                w.website_type = WT_WO
                w.url_subdomain = bw.web_url_subdomain
                w.url_domain = bw.web_url_domain
                w.url_suffix = bw.web_url_suffix
                #w.txt = bw.web_txt
                w.txt = '.'.join(filter(None,
                                        [w.url_subdomain,
                                         w.url_domain,
                                         w.url_suffix]))
        
        
                w.save()
                
                if e_created:
                    # mark as 'main' only for newly created employer
                    w.mark_as_main()
                
                if DEBUG: print w
    
    #
    # add bw webprofile
    #
    if bw.is_public:
        st = ST_BW
    else:
        st = ST_BP
        
    wp_url = st.url + bw.ticker
    wp, wp_created = EmpWebprofile.objects.get_or_create(employer=employer, webprofile_type=WP_BW,
                                             defaults={'url': wp_url, 'description': bw.ticker})
    if not wp_created:
        wp.url = wp_url
        wp.description = bw.ticker
        wp.save()
    
    # if no sh_links exist, add sh_link and publish
    if not employer.links.exists():
        # let's create unique link
        link = None
        if bw.web_url is not None:
            link = bw.web_url_domain # first candidate
            if ShLink.objects.filter(link=link).exists():
                link += '-' + bw.web_url_suffix.replace('.', '-')
                if ShLink.objects.filter(link=link).exists():
                    if bw.is_public:
                        link += '-' + slugify(bw.ticker_t.replace('_', ' '))
                    if ShLink.objects.filter(link=link).exists():
                        link = None # hmm... ?? it should NEVER arrive here!
        
        if link is None:
            # that should nail it...
            
            link = slugify(' '.join([bw.name, bw.dedup]).replace('_', ' '))
            
        
        sh_link = ShLink.objects.create(employer=employer, link=link)
        sh_link.publish()
        
        
    if DEBUG: print employer.get_published_link(), "\n"