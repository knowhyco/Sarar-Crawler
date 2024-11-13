import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import os
import time
from urllib.parse import urljoin
import logging
from typing import List, Set
from datetime import datetime

class SitemapCrawler:
    def __init__(self, output_path: str = "C:\\sarar_urun2"):
        self.output_path = output_path
        self.visited_urls: Set[str] = set()
        
        # Loglama için klasör oluştur
        self.log_dir = os.path.join(output_path, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Log dosyası ayarları
        log_file = os.path.join(self.log_dir, f'crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Crawler başlatılıyor...")
        self.logger.info(f"Çıktı klasörü: {output_path}")
        self.logger.info(f"Log dosyası: {log_file}")

    def fetch_url(self, url: str) -> str:
        """
        Verilen URL'den içeriği getirir ve hata durumlarını yönetir.
        """
        self.logger.debug(f"URL getiriliyor: {url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            self.logger.debug(f"URL başarıyla getirildi: {url} (Status: {response.status_code})")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"URL'ye erişilirken hata oluştu {url}: {str(e)}")
            return ""

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Sitemap'ten URL'leri ayıklar.
        """
        self.logger.info(f"Sitemap ayrıştırılıyor: {sitemap_url}")
        urls = []
        content = self.fetch_url(sitemap_url)
        
        if not content:
            self.logger.error("Sitemap içeriği boş!")
            return urls

        try:
            root = ET.fromstring(content)
            namespace = root.tag.split('}')[0] + '}'
            self.logger.debug(f"XML namespace: {namespace}")
            
            # URL'leri topla
            url_elements = root.findall(f'.//{namespace}url')
            self.logger.info(f"Bulunan URL sayısı: {len(url_elements)}")
            
            for url in url_elements:
                loc = url.find(f'{namespace}loc')
                if loc is not None and loc.text not in self.visited_urls:
                    self.logger.debug(f"Yeni URL bulundu: {loc.text}")
                    urls.append(loc.text)
            
        except ET.ParseError as e:
            self.logger.error(f"Sitemap ayrıştırılırken hata oluştu: {str(e)}")
            
        self.logger.info(f"Toplam bulunan benzersiz URL sayısı: {len(urls)}")
        return urls

    def extract_content(self, html: str, url: str) -> tuple:
        """
        HTML'den sadece blog-single-content div'i içindeki içeriği çıkarır.
        Returns: (başlık, içerik) tuple'ı
        """
        self.logger.debug(f"İçerik çıkarma başlıyor: {url}")
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Sadece blog-single-content div'ini bul
            content_div = soup.find('div', class_='blog-single-content')
            if not content_div:
                self.logger.warning(f"blog-single-content div'i bulunamadı: {url}")
                return None, None
            
            # Başlığı al (h2 etiketinden)
            title = content_div.find('h2')
            title = title.text.strip() if title else 'Başlık bulunamadı'
            
            # İçeriği temizle ve formatla
            content_text = []
            
            # Tüm paragraf ve başlıkları topla
            for element in content_div.find_all(['p', 'h2']):
                if element.name == 'h2':
                    # Başlıkları belirgin yap
                    content_text.append(f"\n### {element.text.strip()} ###\n")
                else:
                    # Normal paragrafları ekle
                    text = element.text.strip()
                    if text:  # Boş paragrafları atlama
                        content_text.append(text)
            
            final_content = '\n\n'.join(content_text)
            
            if not final_content:
                self.logger.warning(f"İçerik boş: {url}")
                return None, None
                
            return title, final_content
            
        except Exception as e:
            self.logger.error(f"İçerik çıkarılırken hata oluştu: {str(e)}")
            return None, None

    def crawl_and_save(self, sitemap_url: str) -> None:
        """
        Sitemap'i crawl eder ve içerikleri bir dosyada birleştirir.
        """
        self.logger.info(f"Crawling başlatılıyor: {sitemap_url}")
        
        try:
            os.makedirs(self.output_path, exist_ok=True)
            output_file = os.path.join(self.output_path, "blog_contents.txt")
            self.logger.info(f"Çıktı dosyası: {output_file}")
            
            urls = self.parse_sitemap(sitemap_url)
            total_urls = len(urls)
            self.logger.info(f"İşlenecek toplam URL sayısı: {total_urls}")
            
            processed_urls = 0
            successful_urls = 0
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for index, url in enumerate(urls, 1):
                    if url in self.visited_urls:
                        continue
                        
                    self.logger.info(f"İşleniyor [{index}/{total_urls}]: {url}")
                    
                    html_content = self.fetch_url(url)
                    if html_content:
                        title, extracted_content = self.extract_content(html_content, url)
                        if title and extracted_content:
                            f.write("\n" + "-"*100 + "\n")
                            f.write(f"BAŞLIK: {title}\n")
                            f.write(f"URL: {url}\n")
                            f.write("-"*100 + "\n\n")
                            f.write(extracted_content)
                            f.write("\n\n")
                            successful_urls += 1
                            self.logger.info(f"İçerik başarıyla kaydedildi: {url}")
                    
                    processed_urls += 1
                    self.visited_urls.add(url)
                    
                    # İlerleme durumunu göster
                    progress = (processed_urls / total_urls) * 100
                    self.logger.info(f"İlerleme: %{progress:.2f} ({processed_urls}/{total_urls})")
                    
                    time.sleep(1)
            
            # Final özeti
            self.logger.info("="*50)
            self.logger.info("CRAWLING TAMAMLANDI - ÖZET")
            self.logger.info(f"Toplam URL sayısı: {total_urls}")
            self.logger.info(f"İşlenen URL sayısı: {processed_urls}")
            self.logger.info(f"Başarılı URL sayısı: {successful_urls}")
            self.logger.info(f"Başarı oranı: %{(successful_urls/total_urls*100):.2f}")
            self.logger.info(f"Çıktı dosyası: {output_file}")
            self.logger.info("="*50)
            
        except Exception as e:
            self.logger.error(f"Crawling sırasında beklenmeyen hata: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    try:
        sitemap_url = input("Sitemap URL'sini girin: ")
        
        if not sitemap_url.startswith(('http://', 'https://')):
            raise ValueError("Geçersiz URL! URL 'http://' veya 'https://' ile başlamalıdır.")
        
        crawler = SitemapCrawler()
        crawler.crawl_and_save(sitemap_url)
        
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"Program hatası: {str(e)}")
        logging.error("Program hatası:", exc_info=True)