from django.contrib import admin
from django import forms

# https://github.com/john-kurkowski/tldextract
# https://pypi.python.org/pypi/tldextract
import tldextract

from common_models_employers.models.employers \
    import  Employer

from common_models_employers.models.sh_data \
    import  ShDisplayName, ShLink, ShPublishedLink, ShLinkUSState, \
            ShJobsMap, ShDescription, ShSnapshotFactType, ShSnapshotFact

from common_models_employers.models.emp_data \
    import EmpWebsiteType, EmpWebsite, EmpWebprofileType, EmpWebprofile

from common_models_employers.models.ref_data \
    import USState

class ShDisplayNameInline(admin.TabularInline):
    model = ShDisplayName
    extra = 0

class ShLinkForm(forms.ModelForm):
    class Meta:
        model = ShLink

class ExpandedShLinkForm(ShLinkForm):
    to_publish = forms.BooleanField(initial=False, required=False, label='Publish?',
                                    help_text='Select one to publish.')

    def save(self, force_insert=False, force_update=False, commit=True):
        sh_link = super(ShLinkForm, self).save(commit=True)
        if self.cleaned_data.get('to_publish'):
            sh_link.publish()
        return sh_link


class ShLinkInline(admin.TabularInline):
    model = ShLink
    extra = 0
    form = ExpandedShLinkForm
    fields = ('link', 'datetime_created', 'is_published', 'to_publish',)
    readonly_fields = ('datetime_created', 'is_published',)

class ShPublishedLinkInline(admin.StackedInline):
    model = ShPublishedLink
    extra = 0

class ShJobsMapInline(admin.TabularInline):
    model = ShJobsMap
    extra = 0

class ShDescriptionInline(admin.TabularInline):
    model = ShDescription
    extra = 0

class ShSnapshotFactInline(admin.TabularInline):
    model = ShSnapshotFact
    extra = 0

class EmpWebsiteForm(forms.ModelForm):
    class Meta:
        model = EmpWebsite

class ExpandedEmpWebsiteForm(EmpWebsiteForm):
    to_mark_as_main = forms.BooleanField(initial=False, required=False, label='Mark As Main?',
                                    help_text='Select one to mark as main.')
    
    def save(self, force_insert=False, force_update=False, commit=True):
        emp_website = super(EmpWebsiteForm, self).save(commit=True)
        
        url = self.cleaned_data.get('url')
        ext = tldextract.extract(url)
        emp_website.url_subdomain = ext.subdomain if ext.subdomain != '' else None
        emp_website.url_domain = ext.domain
        emp_website.url_suffix = '-' if ext.suffix == '' else ext.suffix
        
        emp_website.txt = '.'.join(filter(None,
                                        [emp_website.url_subdomain,
                                         emp_website.url_domain,
                                         emp_website.url_suffix]))
        
        #dedup = self.cleaned_data.get('dedup')
        #emp_website.dedup = dedup if dedup != '' else None
        
        emp_website.save()
        
        if self.cleaned_data.get('to_mark_as_main'):
            emp_website.mark_as_main()
            
        return emp_website

class EmpWebsiteInline(admin.TabularInline):
    model = EmpWebsite
    extra = 0
    form = ExpandedEmpWebsiteForm
    readonly_fields = ('is_marked_as_main', 'dedup',
                       'txt', 'url_subdomain', 'url_domain', 'url_suffix',)

from urlparse import urlparse

class EmpWebprofileForm(forms.ModelForm):
    class Meta:
        model = EmpWebprofile
        
    def save(self, force_insert=False, force_update=False, commit=True):
        emp_webprofile = super(EmpWebprofileForm, self).save(commit=True)
        
        wpt = self.cleaned_data.get('webprofile_type')
        if wpt.code == 'tw':
            url = self.cleaned_data.get('url')
            handle = urlparse(url).path.split('/')[1]
            emp_webprofile.description = handle
            emp_webprofile.url = "http://www.twitter.com/" + handle
        emp_webprofile.save()
        return emp_webprofile
        
class EmpWebprofileInline(admin.TabularInline):
    model = EmpWebprofile
    extra = 0
    form = EmpWebprofileForm
    
        
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_unique_name', 'get_display_name',
                    'main_website_link',
                    'employer_info_link', 'is_published',
                    'is_gplus', 'is_linkedin', 'is_facebook', 'is_twitter',
                    'is_sh_description', 'is_mapped', 'bw_profile_link', 'get_traded_as')
    list_display_links = ('id', 'get_unique_name')
    #list_filter = ['name']
    search_fields = ['name', '=id']
    list_per_page = 25
    save_on_top = True
    
    inlines = [ShDisplayNameInline, ShLinkInline, ShJobsMapInline,
               ShDescriptionInline, ShSnapshotFactInline,
               EmpWebsiteInline, EmpWebprofileInline]#, ShPublishedLinkInline]

    
    def main_website_link(self, obj):
        mw = obj.get_main_website()
        if mw is None:
            info = ''
        else:
            info =  '<a style="color: purple;" href="%s" target="_blank">%s</a>' \
                         % (mw.website.url, mw.website.txt)
        return info    
    main_website_link.allow_tags = True
    
    def employer_info_link(self, obj):
        emp_link = obj.get_published_link()
        info = emp_link
        if obj.is_published():
            emp_href = "http://www.simplyhired.com/employer-info-%s.html" % (emp_link)
            info =  '<a style="color: green;" href="%s" target="_blank">%s</a>' \
                         % (emp_href, emp_link)
            for des in obj.get_all_descriptions():
                info += '<br/>' + des[:37]
        return info    
    employer_info_link.allow_tags = True
    
    def bw_profile_link(self, obj):
        bw_id = obj.get_bw_id()
        info = bw_id
        if bw_id != '':
            href = obj.get_bw_url()
            info =  '<a style="color: green;" href="%s" target="_blank">%s</a>' \
                         % (href, bw_id)
        return info    
    bw_profile_link.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        #dedup = form.cleaned_data.get('dedup')
        #obj.dedup = dedup if dedup != '' else None
        
        obj.save()


class ShLinkUSStateInline(admin.TabularInline):
    model = ShLinkUSState
    extra = 0
    
class USStateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_link', 'capital', 'largest_city',
                    'status', 'founded', 'population')
    save_on_top = True
    inlines = [ShLinkUSStateInline]
    
admin.site.register(Employer, EmployerAdmin)
admin.site.register(EmpWebsiteType)
admin.site.register(EmpWebprofileType)
admin.site.register(ShSnapshotFactType)
admin.site.register(USState, USStateAdmin)

#
# EmpWebsite
#
class EmpWebsiteAdmin(admin.ModelAdmin):
    list_display = ('employer', 'url', 'txt',
                    'url_subdomain', 'url_domain', 'url_suffix',
                    'description', 'website_type', 'dedup', 'is_marked_as_main',)
    list_display_links = ('url', )
    list_filter = ['url_suffix', 'dedup']
    search_fields = ['url', 'txt']
    list_per_page = 20
    save_on_top = True
    
    fields = list_display
    readonly_fields = ('employer', 'url', 'txt',
                       'url_subdomain', 'url_domain', 'url_suffix',
                       'is_marked_as_main',)

admin.site.register(EmpWebsite, EmpWebsiteAdmin)

#
#
#
from common_models_employers.models.sh_data import  ShRating
class ShRatingAdmin(admin.ModelAdmin):
    list_display = ('get_employer_id', 'employer_admin_link', 'get_employer_display_name',
                    'rating',
                    'employer_info_link', 'main_website_link')
    list_editable = ('rating',)
    list_display_links = ('main_website_link', )
    list_filter = ('rating',)
    search_fields = ['employer__name', '=employer__id']
    list_per_page = 10
    save_on_top = True
    
    readonly_fields = ('employer',)
    
    def get_employer_id(self, obj):
        return obj.employer.id
    get_employer_id.short_description = 'Employer ID'
    
    def employer_admin_link(self, obj):
        emp_name = obj.employer.name
        emp_id = obj.employer.pk
        emp_href = "/admin/common_models_employers/employer/%s/" % (emp_id)
        return '<a style="color: #5b80b2; font-weight: bold;" href="%s" target="_blank">%s</a>' \
                         % (emp_href, emp_name)
    employer_admin_link.allow_tags = True
    employer_admin_link.short_description = 'Employer Admin Link'
    
    def get_employer_display_name(self, obj):
        return obj.employer.get_display_name()
    get_employer_display_name.short_description = 'Employer Display Name'
    
    
    def employer_info_link(self, obj):
        emp_link = obj.employer.get_published_link()
        info = emp_link
        if obj.employer.is_published():
            emp_href = "http://www.simplyhired.com/employer-info-%s.html" % (emp_link)
            info =  '<a style="color: green; font-weight: bold;" href="%s" target="_blank">%s</a>' \
                         % (emp_href, emp_link)
            for des in obj.employer.get_all_descriptions():
                info += '<br/><span style="font-size: 0.75em;">' + des[:57] + " ...</span>"
        return info 
    employer_info_link.allow_tags = True
    employer_info_link.short_description = "Employer SH Profile Link"
    
    def main_website_link(self, obj):
        mw = obj.employer.get_main_website()
        if mw is None:
            info = ''
        else:
            info =  '<a style="color: #0066cc; font-weight: normal;" href="%s" target="_blank">%s</a>' \
                         % (mw.website.url, mw.website.txt)
        return info    
    main_website_link.allow_tags = True
    main_website_link.short_description = "Employer Main Website"
    
admin.site.register(ShRating, ShRatingAdmin)

#
# JobsCompany
#
from common_models_employers.models.sh_jobs import  JobsCompany

class JobsCompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'normalized_company_name', 'canonical_company_name','employer',
                    'domain', 'domain_subdomain', 'domain_domain', 'domain_suffix',
                    'done',)
                    #'url', 'company_hash',
                    #'parent', 'source_type', 'c_type', 'page_title', 'validate',
                    #'ppr_validated')
    list_display_links = ('id', 'normalized_company_name')
    list_filter = ['done', 'domain_suffix']
    search_fields = ['normalized_company_name', 'domain', 'canonical_company_name']
    list_per_page = 30
    save_on_top = True
    
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('id', 'normalized_company_name', 'canonical_company_name',
                       'employer',
                       'domain', 'domain_subdomain', 'domain_domain', 'domain_suffix',
                       'url', 'company_hash',
                       'parent', 'source_type', 'c_type', 'page_title',
                       'validate', 'ppr_validated')
        }),
    )
    
    readonly_fields = ('id', 'normalized_company_name', 'canonical_company_name',
                       'employer',
                       'domain', 'domain_subdomain', 'domain_domain', 'domain_suffix',
                       'url', 'company_hash',
                       'parent', 'source_type', 'c_type', 'page_title',
                       'validate', 'ppr_validated')
                    
                    
admin.site.register(JobsCompany, JobsCompanyAdmin)


#
# SrcBwPublic
#
from common_models_employers.models.src_data import SrcSourceType, SrcBwPublic

admin.site.register(SrcSourceType)

class SrcBwPublicAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'country',
                    'is_public',
                    'ticker',
                    'ticker_t',
                    'ticker_e',
                    'web_txt',
                    'web_url',
                    'web_url_subdomain',
                    'web_url_domain',
                    'web_url_suffix',
                    'capital_iq_industry',
                    'industry',
                    'industry_code',
                    'sector',
                    'sector_code',
                    'is_short_description',
                    'employees_date',
                    'employees_num',
                    'exchange',
                    'hq_address',
                    'phone',
                    'year_founded',)
    list_filter = ['is_public', 'region', 'capital_iq_industry']
    search_fields = ['name', 'web_url', 'ticker']
    list_per_page = 30
    save_on_top = True

admin.site.register(SrcBwPublic, SrcBwPublicAdmin)
    
    
    
    
    
    
    
    