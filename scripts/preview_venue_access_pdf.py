"""Generate synthetic cards using locally configured event logos."""
from pathlib import Path
import sys
from contextlib import ExitStack
from reportlab.lib.utils import ImageReader
from unittest.mock import patch
from flask import Flask
from sqlalchemy import create_engine, select
from config import Config
from app.models.system_setting import SystemSetting
from app.services.venue_access_pdf import build_access_card, build_access_cards

if __name__ == '__main__':
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as connection:
        logos = dict(connection.execute(select(SystemSetting.key, SystemSetting.value).where(
            SystemSetting.key.in_(['school_logo_path','expo_logo_path']))).all())
    engine.dispose()
    app = Flask('app')
    with app.app_context(), ExitStack() as stack:
        stack.enter_context(patch('app.services.venue_access_pdf.SystemSetting.get_value',side_effect=lambda key,default='':logos.get(key,default)))
        if '--production-logos' in sys.argv:
            images = {'school_logo_path':ImageReader('tmp/pdfs/corvec.jpg'),'expo_logo_path':ImageReader('tmp/pdfs/expotecnica.png')}
            stack.enter_context(patch('app.services.venue_access_pdf._brand_logo',side_effect=images.get))
        folder = Path('tmp/pdfs'); folder.mkdir(parents=True,exist_ok=True)
        for label,venue in [('venue-access',{'name':'P1-A4','responsible':'Carlos Ticas'}),('venue-access-long',{'name':'Recinto de proyectos innovadores '*3,'responsible':'Nombre completo del responsable '*3})]:
            data = build_access_card(venue,'https://expotecnica-regionaldesamparados.com/expo/recinto/eyJ2ZW51ZSI6IjEyMzQ1Njc4OSIsIm5vbmNlIjoiMTIzNDU2Nzg5MDEyMzQ1Njc4OTAifQ.example-signature')
            (folder/(label+'.pdf')).write_bytes(data.getvalue())
        print('PDF previews generated with configured logos:', sorted(logos))
        entries = [({'name':f'P1-A{index+4}','responsible':name},'https://expotecnica-regionaldesamparados.com/r/1234567890abcdefghijkl') for index,name in enumerate(['Carlos Ticas','Cinthia Díaz','Yolenny Fonseca','Anaís Cruz','Maryuri Fernández','Katherine Solano','Gabriela Barquero','Víctor Flores Vargas','Luis Diego Arce','Manuel Rivera','Yamileth Sánchez'])]
        entries[-1] = ({'name':'Recinto de proyectos innovadores '*3,'responsible':'Nombre completo del responsable '*3},entries[-1][1])
        (folder/'venue-cards.pdf').write_bytes(build_access_cards(entries).getvalue())
