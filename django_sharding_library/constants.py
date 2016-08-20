class Backends(object):
    MYSQL = ('django.db.backends.mysql', 'django.contrib.gis.db.backends.mysql')
    POSTGRES = ('django.db.backends.postgresql_psycopg2', 'django.db.backends.postgresql', 'django.contrib.gis.db.backends.postgis')
    SQLITE = ('django.db.backends.sqlite3', 'django.contrib.gis.db.backends.spacialite')
