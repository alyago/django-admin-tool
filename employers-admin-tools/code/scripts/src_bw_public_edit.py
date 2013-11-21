"""
Run it:
> python manage.py runscript src_bw_public_edit


Interesting queries:
*
SELECT name FROM src_bw_public GROUP BY name HAVING COUNT(id) > 1
*
"""


from common_models_employers.models.src_data import SrcBwPublic

def run():
    print u'Running src_bw_public_edit...'
    
    #dedup_names()


from django.db import connections
def dedup_names():
    print "For names that appear more than once, set dedup to ticker"

    cursor = connections['employers'].cursor()
    cursor.execute("SELECT name from src_bw_public group by name HAVING COUNT(id) > 1")
    #print cursor.description
    for row in cursor.fetchall():
        name = row[0]
        for bw in SrcBwPublic.objects.filter(name=name).only('name', 'dedup', 'ticker'):
            bw.dedup = bw.ticker
            #print bw.name, bw.dedup
            bw.save()
