import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import time
import logging
from pathlib import Path
import concurrent.futures
import re

class SitemapCrawler:
    def __init__(self, sitemap_url, output_file="crawled_content.txt", max_workers=5, delay=1):
        self.sitemap_url = sitemap_url
        self.output_file = output_file
        self.max_workers = max_workers
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('crawler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_urls_from_sitemap(self, sitemap_url=None):
        """Sitemap'ten URL'leri çeker"""
        try:
            # Eğer sitemap_url parametresi verilmemişse, sınıfın kendi sitemap_url'ini kullan
            current_sitemap = sitemap_url or self.sitemap_url
            
            response = requests.get(current_sitemap, headers=self.headers, verify=False)
            response.raise_for_status()
            
            # XML içeriğini temizle ve parse et
            content = response.content.decode('utf-8')
            content = re.sub(r'xmlns="[^"]+"', '', content)  # namespace'leri kaldır
            root = ET.fromstring(content)
            
            urls = []
            # URL'leri topla
            for url in root.findall('.//loc'):
                urls.append(url.text)
            
            return urls
            
        except Exception as e:
            self.logger.error(f"Sitemap çekilirken hata: {str(e)}")
            return []

    def extract_content(self, url):
        """Verilen URL'den içeriği çeker"""
        try:
            time.sleep(self.delay)
            response = requests.get(url, headers=self.headers, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Blog içeriğini özel olarak bul
            content = soup.find('div', class_='blog-single-content')
            
            if not content:
                content = soup.find('div', class_='content')
            
            if content:
                # Paragrafları ve başlıkları topla
                text_elements = []
                
                # Başlık bilgisini al
                title = soup.find('h1')
                if title:
                    text_elements.append(title.get_text(strip=True))
                
                # İçerik elementlerini topla
                for element in content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    text = element.get_text(strip=True)
                    if text:  # Boş olmayan metinleri ekle
                        text_elements.append(text)
                
                # Tüm metinleri birleştir
                text = '\n\n'.join(text_elements)
                
                return {
                    'url': url,
                    'content': text
                }
            else:
                self.logger.warning(f"İçerik bulunamadı: {url}")
                return None
            
        except Exception as e:
            self.logger.error(f"URL işlenirken hata ({url}): {str(e)}")
            return None

    def save_content(self, content_dict):
        """İçeriği dosyaya kaydeder"""
        if not content_dict:
            return
            
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*80}\n")
                f.write(f"URL: {content_dict['url']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(content_dict['content'])
                
        except Exception as e:
            self.logger.error(f"İçerik kaydedilirken hata: {str(e)}")

    def crawl(self):
        """Ana crawling işlemini başlatır"""
        self.logger.info(f"Crawling başlatılıyor: {self.sitemap_url}")
        
        # Önceki çıktı dosyasını temizle
        Path(self.output_file).unlink(missing_ok=True)
        
        # Sitemap'ten URL'leri al
        urls = self.get_urls_from_sitemap()
        
        if not urls:
            self.logger.error("Sitemap'ten URL alınamadı!")
            return
            
        total_urls = len(urls)
        self.logger.info(f"Toplam {total_urls} URL bulundu")
        
        # Paralel işleme
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.extract_content, url): url for url in urls}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url), 1):
                url = future_to_url[future]
                try:
                    content_dict = future.result()
                    if content_dict:
                        self.save_content(content_dict)
                    self.logger.info(f"İşlenen URL ({i}/{total_urls}): {url}")
                except Exception as e:
                    self.logger.error(f"URL işlenirken hata ({url}): {str(e)}")

def main():
    sitemap_url = "https://blog.sarar.com/post-sitemap.xml"
    crawler = SitemapCrawler(
        sitemap_url=sitemap_url,
        output_file="site_content.txt",
        max_workers=3,  # Paralel işlem sayısını azalttım
        delay=2  # Bekleme süresini artırdım
    )
    crawler.crawl()

if __name__ == "__main__":
    main()