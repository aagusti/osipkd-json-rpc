from types import (
    StringType,
    UnicodeType,
    FloatType,
    IntType,
    )
from sqlalchemy import (
    func,
    Table,
    Column,
    Integer,
    Float,
    DateTime,
    )
    
from sqlalchemy.sql.expression import text 
from pyramid.view import view_config
from pyramid_xmlrpc import XMLRPCView
from pyramid_rpc.jsonrpc import jsonrpc_method
from hashlib import md5

from ..models import (
    DBSession,
    PbbDBSession,
    Base,
    PbbBase,
    CommonModel,
    )
    
from ..tools import (
    dict_to_simple_value,
    date_from_str,
    FixLength,
    get_settings,
    split_tablename,
    DateType,
    DateTimeType,
    )
from ..views import BaseORM, auth_from_rpc
LIMIT = 1000
CODE_OK = 0
CODE_NOT_FOUND = -1
CODE_INVALID_LOGIN = -10


#######        
# PBB #
#######
class PbbORM(BaseORM): # abstract
    def __init__(self, tablename):
        BaseORM.__init__(self, PbbBase, PbbDBSession, tablename)


class PbbInvoice(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_invoice_table)

    def get_profile(self, propinsi, kabupaten, kecamatan, kelurahan, blok, urut,
        jenis, tahun):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan,
               kd_kelurahan=kelurahan, kd_blok=blok, no_urut=urut,
               kd_jns_op=jenis, thn_pajak_sppt=tahun)
        return q.first()

    def get_count(self, awal):
        q = PbbDBSession.query(func.count().label('jml')).filter(
                self.cls.tgl_terbit_sppt==awal)
        return PbbORM.get_count(self, q)

    def get_rows(self, awal, offset=-1):
        q = PbbDBSession.query(self.cls).filter(
                self.cls.tgl_terbit_sppt == awal)
        q = q.order_by('kd_propinsi', 'kd_dati2', 'kd_kecamatan', 'kd_kelurahan',
                'kd_blok', 'no_urut', 'kd_jns_op', 'thn_pajak_sppt')
        return PbbORM.get_rows(self, q, offset)


class PbbPayment(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_payment_table)

    def get_profile(self, propinsi, kabupaten, kecamatan, kelurahan, blok, urut,
        jenis, tahun):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan,
               kd_kelurahan=kelurahan, kd_blok=blok, no_urut=urut,
               kd_jns_op=jenis, thn_pajak_sppt=tahun)
        return q.all()
        
    def get_count(self, tanggal):
        q = PbbDBSession.query(func.count().label('jml')).filter(
                self.cls.tgl_pembayaran_sppt==tanggal)
        return PbbORM.get_count(self, q)

    def get_rows(self, tanggal, offset=0):
        q = PbbDBSession.query(self.cls).filter(
                self.cls.tgl_rekam_byr_sppt==tanggal)
        q = q.order_by('kd_propinsi', 'kd_dati2', 'kd_kecamatan', 'kd_kelurahan',
                'kd_blok', 'no_urut', 'kd_jns_op', 'thn_pajak_sppt',
                'pembayaran_sppt_ke')
        return PbbORM.get_rows(self, q, offset)

class PbbDop(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_dop)

    def get_row(self, propinsi, kabupaten, kecamatan, kelurahan, blok, urut,
        jenis):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan,
               kd_kelurahan=kelurahan, kd_blok=blok, no_urut=urut,
               kd_jns_op=jenis)
        return q.first()
        
class PbbDop(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_dop)

    def get_row(self, propinsi, kabupaten, kecamatan, kelurahan, blok, urut,
        jenis):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan,
               kd_kelurahan=kelurahan, kd_blok=blok, no_urut=urut,
               kd_jns_op=jenis)
        return q.first()

class PbbPropinsi(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_propinsi)

    def get_row(self, propinsi):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi)
        return q.first()

class PbbDati2(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_dati2)

    def get_row(self, propinsi, kabupaten):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten)
        return q.first()

class PbbKecamatan(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_kecamatan)

    def get_row(self, propinsi, kabupaten, kecamatan):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan)
        return q.first()

class PbbKelurahan(PbbORM):
    def __init__(self):
        settings = get_settings()
        PbbORM.__init__(self, settings.pbb_kelurahan)

    def get_row(self, propinsi, kabupaten, kecamatan, kelurahan):
        q = PbbDBSession.query(self.cls).filter_by(kd_propinsi=propinsi,
               kd_dati2=kabupaten, kd_kecamatan=kecamatan,
               kd_kelurahan=kelurahan)
        return q.first()
                
PBB_INVOICE_ID = [
    ('Propinsi', 2, 'N'),
    ('Kabupaten', 2, 'N'),
    ('Kecamatan', 3, 'N'),
    ('Kelurahan', 3, 'N'),
    ('Blok', 3, 'N'),
    ('Urut', 4, 'N'),
    ('Jenis', 1, 'N'),
    ('Tahun Pajak', 4, 'N'),
    ]
     
@jsonrpc_method(method='get_profile', endpoint='pbb')
def get_profile_view(request, nop):
    resp = auth_from_rpc(request)
    if resp['code'] != 0:
        return resp    
    
    invoice_id = FixLength(PBB_INVOICE_ID)
    invoice_id.set_raw(nop.strip())
    inv = PbbInvoice()
    row = inv.get_profile(invoice_id['Propinsi'], invoice_id['Kabupaten'],
            invoice_id['Kecamatan'], invoice_id['Kelurahan'],
            invoice_id['Blok'], invoice_id['Urut'], invoice_id['Jenis'],
            invoice_id['Tahun Pajak'])
    if not row:
        return dict(code=CODE_NOT_FOUND,
                    message='NOP {nop} tidak ada'.format(nop=nop))
    r = dict(code=0, message='OK')
    vals = row.to_dict()
    vals = dict_to_simple_value(vals)
    r.update(vals)
    return r
     
@jsonrpc_method(endpoint='pbb')
def get_profiles(request, tanggal):
    resp = auth_from_rpc(request)
    if resp['code'] != 0:
        return resp    
    
    awal = date_from_str(tanggal)
    inv = PbbInvoice()
    row_count, page_count = inv.get_count(awal)
    if not row_count:
        msg = 'Tidak ada NOP tanggal {awal}'
        msg = msg.format(awal=tanggal)
        return dict(code=CODE_NOT_FOUND, message=msg)
        
    rows = inv.get_rows(awal) #, offset)
    r = dict(code=0, message='OK')
    trxs = []
    for row in rows:
        vals = row.to_dict()
        vals = dict_to_simple_value(vals)
        trxs.append(vals)
    
    r['rows'] = trxs
    return r 

@jsonrpc_method(endpoint='pbb')    
def get_trx(request, nop):
    resp = auth_from_rpc(request)
    if resp['code'] != 0:
        return resp    
    
    invoice_id = FixLength(PBB_INVOICE_ID)
    invoice_id.set_raw(nop.strip())
    pay = PbbPayment()
    rows = pay.get_profile(invoice_id['Propinsi'], invoice_id['Kabupaten'],
              invoice_id['Kecamatan'], invoice_id['Kelurahan'],
              invoice_id['Blok'], invoice_id['Urut'], invoice_id['Jenis'],
              invoice_id['Tahun Pajak'])
            
    if not rows:
        return dict(code=CODE_NOT_FOUND,
                    message='NOP {nop} tidak ada'.format(nop=nop))
    r = dict(code=0, message='OK')
    
    trxs = []
    for row in rows:
        vals = row.to_dict()
        vals = dict_to_simple_value(vals)
        trxs.append(vals)
    r['rows'] = trxs
    return r
    
@jsonrpc_method(endpoint='pbb')
def get_trxs(request, tanggal):
    resp = auth_from_rpc(request)
    if resp['code'] != 0:
        return resp
    
    awal = date_from_str(tanggal)
    pay = PbbPayment()
    row_count, page_count = pay.get_count(awal)
    if not row_count:
        msg = 'Tidak ada pembayaran di tanggal {awal}'
        msg = msg.format(awal=tanggal)
        return dict(code=CODE_NOT_FOUND, message=msg)

    rows = pay.get_rows(tanggal)
    r = dict(code=0, message='OK')
    trxs = []
    for row in rows:
        vals = row.to_dict()
        vals = dict_to_simple_value(vals)
        trxs.append(vals)

    r['rows'] = trxs
    return r 
    
@jsonrpc_method(endpoint='pbb')
def get_ipbb(request, nop):
    resp = auth_from_rpc(request)
    if resp['code'] != 0:
        return resp    
    
    invoice_id = FixLength(PBB_INVOICE_ID)
    invoice_id.set_raw(nop.strip())
    inv = PbbInvoice()
    row = inv.get_profile(invoice_id['Propinsi'], invoice_id['Kabupaten'],
            invoice_id['Kecamatan'], invoice_id['Kelurahan'],
            invoice_id['Blok'], invoice_id['Urut'], invoice_id['Jenis'],
            invoice_id['Tahun Pajak'])
    if not row:
        return dict(code=CODE_NOT_FOUND,
                    message='NOP {nop} tidak ada'.format(nop=nop))
                    
    r = dict(code=0, message='OK')
    vals = row.to_dict()
    vals = dict_to_simple_value(vals)
    
    r2 = PbbDop()
    r1 = r2.get_row(invoice_id['Propinsi'], invoice_id['Kabupaten'],
            invoice_id['Kecamatan'], invoice_id['Kelurahan'],
            invoice_id['Blok'], invoice_id['Urut'], invoice_id['Jenis'])
            
    vals['jalan_op']=r1 and r1.jalan_op  or ""
    vals['blok_kav_no_op']=r1 and r1.blok_kav_no_op or ""
    vals['rw_op']=r and r1.rw_op or ""
    vals['rt_op']=r and r1.rt_op or ""
    
    r2 = PbbKelurahan()
    r1 = r2.get_row(invoice_id['Propinsi'], invoice_id['Kabupaten'],
            invoice_id['Kecamatan'], invoice_id['Kelurahan'])
    vals['nm_kelurahan']=r1 and r1.nm_kelurahan or ""
    
    r2 = PbbKecamatan()
    r1 = r2.get_row(invoice_id['Propinsi'], invoice_id['Kabupaten'],
            invoice_id['Kecamatan'])
    vals['nm_kecamatan']=r1 and r1.nm_kecamatan or ""
    
    r2 = PbbDati2()
    r1 = r2.get_row(invoice_id['Propinsi'], invoice_id['Kabupaten'])
    vals['nm_dati2']=r1 and r1.nm_dati2 or ""
    
    r2 = PbbPropinsi()
    r1 = r2.get_row(invoice_id['Propinsi'])
    vals['nm_propinsi']=r1 and r1.nm_propinsi or ""
    r.update(vals)
    return r
