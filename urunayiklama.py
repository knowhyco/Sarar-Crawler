import xml.etree.ElementTree as ET
import csv
import os
import requests
from io import StringIO
import html

def fetch_xml_content(url):
    """URL'den XML içeriğini çeker"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'  # Encoding'i UTF-8 olarak ayarla
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"XML verisi çekilirken hata oluştu: {e}")
        return None

def decode_html_entities(text):
    """HTML entitylerini decode eder"""
    if text is None:
        return ""
    return html.unescape(text)

def clean_cdata(text):
    """CDATA içeriğini temizler ve Türkçe karakterleri düzeltir"""
    if text is None:
        return ""
    # CDATA etiketlerini kaldır
    text = text.replace('<![CDATA[', '').replace(']]>', '')
    # HTML entitylerini decode et
    text = decode_html_entities(text)
    # Türkçe karakter dönüşümlerini yap
    text = text.replace('&uuml;', 'ü').replace('&Uuml;', 'Ü')
    text = text.replace('&ouml;', 'ö').replace('&Ouml;', 'Ö')
    text = text.replace('&ccedil;', 'ç').replace('&Ccedil;', 'Ç')
    text = text.replace('&yacute;', 'ı').replace('&Yacute;', 'İ')
    text = text.replace('&sect;', 'ş').replace('&Sect;', 'Ş')
    text = text.replace('&gbreve;', 'ğ').replace('&Gbreve;', 'Ğ')
    return text.strip()

def parse_description(desc):
    """Ürün açıklamasını temizler ve formatlar"""
    if desc is None:
        return ""
    # HTML etiketlerini kaldır
    desc = decode_html_entities(desc)
    desc = desc.replace('<ul>', '').replace('</ul>', '')
    desc = desc.replace('<li>', '').replace('</li>', '-')
    desc = desc.replace('<br />', ' ').replace('<p>', '').replace('</p>', ' ')
    desc = desc.replace('<strong>', '').replace('</strong>', '')
    desc = desc.replace('<span>', '').replace('</span>', '')
    
    # Fazla boşlukları ve tireleri temizle
    parts = [x.strip() for x in desc.split('-') if x.strip()]
    desc = ' - '.join(parts)
    
    return desc

def process_xml(xml_content):
    """XML içeriğini işler ve ürünleri cinsiyete göre gruplar"""
    try:
        # XML içeriğini parse et
        root = ET.fromstring(xml_content.encode('utf-8'))
        
        products_by_gender = {
            'erkek': [],
            'kadın': [],
            'üniseks': [],
            'belirsiz': []
        }
        
        # Her ürünü işle
        for item in root.findall('.//item'):
            try:
                gender = clean_cdata(item.find('.//{http://base.google.com/ns/1.0}gender').text).lower()
                title = clean_cdata(item.find('.//{http://base.google.com/ns/1.0}title').text)
                link = clean_cdata(item.find('.//{http://base.google.com/ns/1.0}link').text)
                price = clean_cdata(item.find('.//{http://base.google.com/ns/1.0}price').text)
                description = parse_description(clean_cdata(item.find('.//{http://base.google.com/ns/1.0}description').text))
                
                # Boş değerleri kontrol et
                if not title.strip() or not link.strip():
                    continue
                
                product_data = [
                    gender,
                    title,
                    link,
                    price,
                    description
                ]
                
                # Cinsiyete göre grupla
                if 'erkek' in gender.lower():
                    products_by_gender['erkek'].append(product_data)
                elif 'kadın' in gender.lower() or 'kadin' in gender.lower():
                    products_by_gender['kadın'].append(product_data)
                elif 'unisex' in gender.lower() or 'üniseks' in gender.lower():
                    products_by_gender['üniseks'].append(product_data)
                else:
                    products_by_gender['belirsiz'].append(product_data)
                    
            except AttributeError as e:
                print(f"Ürün verileri işlenirken hata oluştu: {e}")
                continue
                
        return products_by_gender
    
    except ET.ParseError as e:
        print(f"XML parse edilirken hata oluştu: {e}")
        return None

def save_to_csv(products, output_dir):
    """Ürünleri CSV dosyalarına kaydeder"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        headers = ['Cinsiyet', 'Ürün Adı', 'Ürün Satın Alma Linki', 'Ürün Fiyatı', 'Ürün Açıklaması']
        
        for gender, products_list in products.items():
            if products_list:
                output_file = os.path.join(output_dir, f'sarar_{gender}_urunler.csv')
                
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:  # UTF-8 with BOM
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(products_list)
                print(f"{gender.capitalize()} ürünleri için CSV dosyası oluşturuldu: {output_file}")
                print(f"Toplam {len(products_list)} ürün kaydedildi.")
                
    except Exception as e:
        print(f"CSV dosyası kaydedilirken hata oluştu: {e}")

def main():
    xml_url = "https://sarar.com/connectprof/tdlb6h1c_yapayzeka"
    output_dir = r"C:\sarar_urun2"
    
    print("XML verisi çekiliyor...")
    xml_content = fetch_xml_content(xml_url)
    
    if xml_content:
        print("XML verisi başarıyla çekildi, işleniyor...")
        products = process_xml(xml_content)
        
        if products:
            print("Veriler işlendi, CSV dosyaları oluşturuluyor...")
            save_to_csv(products, output_dir)
            print(f"\nİşlem tamamlandı! Tüm dosyalar şu dizine kaydedildi: {output_dir}")
        else:
            print("Veriler işlenemedi!")
    else:
        print("XML verisi çekilemedi!")

if __name__ == "__main__":
    main()