import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.settings import get_database_url

#!/usr/bin/env python3
"""
Advanced Strain Scraper for THCA Platform

Scrapes strain data from multiple sources:
- Leafly (most comprehensive)
- Wikileaf (good for lineage)
- AllBud (alternative source)

Features:
- Automatic lineage discovery
- Terpene profiles
- Effects and medical benefits
- Flavor and aroma descriptions
- Retry logic and rate limiting
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrainData:
    name: str
    normalized_name: str
    parent1: Optional[str] = None
    parent2: Optional[str] = None
    strain_type: Optional[str] = None  # Indica, Sativa, Hybrid
    indica_percentage: Optional[float] = None
    sativa_percentage: Optional[float] = None
    description: Optional[str] = None
    flavor_profile: Optional[str] = None
    aroma_profile: Optional[str] = None
    primary_terpenes: Optional[List[str]] = None
    effects: Optional[List[str]] = None
    medical_benefits: Optional[List[str]] = None
    thc_range: Optional[Tuple[float, float]] = None
    cbd_range: Optional[Tuple[float, float]] = None
    scraped_from: List[str] = None
    
    def __post_init__(self):
        if self.scraped_from is None:
            self.scraped_from = []
        if self.primary_terpenes is None:
            self.primary_terpenes = []
        if self.effects is None:
            self.effects = []
        if self.medical_benefits is None:
            self.medical_benefits = []


class StrainScraper:
    """Multi-source strain data scraper"""
    
    def __init__(self, cache_file: str = "strain_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_cache(self) -> Dict:
        """Load cached strain data"""
        if self.cache_file.exists():
            with self.cache_file.open('r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """Save strain cache to disk"""
        with self.cache_file.open('w') as f:
            json.dump(self.cache, f, indent=2, default=str)
    
    def normalize_strain_name(self, name: str) -> str:
        """Normalize strain name for caching and lookup"""
        return re.sub(r'[^a-z0-9]', '', name.lower())
    
    def scrape_strain(self, strain_name: str, force_refresh: bool = False) -> Optional[StrainData]:
        """
        Scrape strain data from multiple sources and merge results
        """
        normalized = self.normalize_strain_name(strain_name)
        
        # Check cache
        if not force_refresh and normalized in self.cache:
            logger.info(f"Using cached data for {strain_name}")
            return StrainData(**self.cache[normalized])
        
        logger.info(f"Scraping {strain_name} from multiple sources...")
        
        # Try each source
        data = StrainData(
            name=strain_name,
            normalized_name=normalized
        )
        
        # Try Leafly first (most comprehensive)
        leafly_data = self.scrape_leafly(strain_name)
        if leafly_data:
            data = self.merge_strain_data(data, leafly_data)
        
        # Try Wikileaf for additional lineage info
        wikileaf_data = self.scrape_wikileaf(strain_name)
        if wikileaf_data:
            data = self.merge_strain_data(data, wikileaf_data)
        
        # Try AllBud as fallback
        allbud_data = self.scrape_allbud(strain_name)
        if allbud_data:
            data = self.merge_strain_data(data, allbud_data)
        
        # Cache the result
        self.cache[normalized] = asdict(data)
        self.save_cache()
        
        return data
    
    def merge_strain_data(self, existing: StrainData, new: StrainData) -> StrainData:
        """Merge data from multiple sources, preferring non-None values"""
        for field in ['parent1', 'parent2', 'strain_type', 'indica_percentage', 'sativa_percentage',
                      'description', 'flavor_profile', 'aroma_profile']:
            if getattr(existing, field) is None and getattr(new, field) is not None:
                setattr(existing, field, getattr(new, field))
        
        # Merge lists
        if new.primary_terpenes:
            existing.primary_terpenes = list(set(existing.primary_terpenes + new.primary_terpenes))
        if new.effects:
            existing.effects = list(set(existing.effects + new.effects))
        if new.medical_benefits:
            existing.medical_benefits = list(set(existing.medical_benefits + new.medical_benefits))
        
        # Track sources
        if new.scraped_from:
            existing.scraped_from.extend(new.scraped_from)
            existing.scraped_from = list(set(existing.scraped_from))
        
        return existing
    
    def scrape_leafly(self, strain_name: str) -> Optional[StrainData]:
        """Scrape data from Leafly"""
        try:
            # Leafly URL format
            url_name = strain_name.lower().replace(' ', '-').replace("'", "")
            url = f"https://www.leafly.com/strains/{url_name}"
            
            logger.info(f"Fetching Leafly: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Leafly returned {response.status_code} for {strain_name}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = StrainData(
                name=strain_name,
                normalized_name=self.normalize_strain_name(strain_name),
                scraped_from=['Leafly']
            )
            
            # Extract strain type (Indica/Sativa/Hybrid)
            strain_type_elem = soup.find('div', class_='strain-type')
            if strain_type_elem:
                type_text = strain_type_elem.get_text(strip=True)
                if 'Indica' in type_text:
                    data.strain_type = 'Indica'
                    # Try to extract percentage
                    match = re.search(r'(\d+)%\s*Indica', type_text)
                    if match:
                        data.indica_percentage = float(match.group(1))
                        data.sativa_percentage = 100 - data.indica_percentage
                elif 'Sativa' in type_text:
                    data.strain_type = 'Sativa'
                    match = re.search(r'(\d+)%\s*Sativa', type_text)
                    if match:
                        data.sativa_percentage = float(match.group(1))
                        data.indica_percentage = 100 - data.sativa_percentage
                elif 'Hybrid' in type_text:
                    data.strain_type = 'Hybrid'
            
            # Extract lineage/genetics
            lineage_section = soup.find('section', {'data-testid': 'lineage'})
            if lineage_section:
                parent_links = lineage_section.find_all('a', href=re.compile(r'/strains/'))
                if len(parent_links) >= 2:
                    data.parent1 = parent_links[0].get_text(strip=True)
                    data.parent2 = parent_links[1].get_text(strip=True)
                elif len(parent_links) == 1:
                    data.parent1 = parent_links[0].get_text(strip=True)
            
            # Extract description
            description_elem = soup.find('div', class_='description')
            if description_elem:
                data.description = description_elem.get_text(strip=True)
            
            # Extract flavors
            flavor_section = soup.find('section', {'data-testid': 'flavors'})
            if flavor_section:
                flavors = [elem.get_text(strip=True) for elem in flavor_section.find_all('span', class_='flavor')]
                data.flavor_profile = ', '.join(flavors) if flavors else None
            
            # Extract aromas
            aroma_section = soup.find('section', {'data-testid': 'aromas'})
            if aroma_section:
                aromas = [elem.get_text(strip=True) for elem in aroma_section.find_all('span', class_='aroma')]
                data.aroma_profile = ', '.join(aromas) if aromas else None
            
            # Extract effects
            effects_section = soup.find('section', {'data-testid': 'effects'})
            if effects_section:
                data.effects = [elem.get_text(strip=True) for elem in effects_section.find_all('span', class_='effect')]
            
            # Extract terpenes
            terpene_section = soup.find('section', {'data-testid': 'terpenes'})
            if terpene_section:
                data.primary_terpenes = [elem.get_text(strip=True) for elem in terpene_section.find_all('span', class_='terpene')]
            
            time.sleep(1)  # Rate limiting
            return data
            
        except Exception as e:
            logger.error(f"Error scraping Leafly for {strain_name}: {e}")
            return None
    
    def scrape_wikileaf(self, strain_name: str) -> Optional[StrainData]:
        """Scrape data from Wikileaf"""
        try:
            url_name = strain_name.lower().replace(' ', '-')
            url = f"https://www.wikileaf.com/strain/{url_name}/"
            
            logger.info(f"Fetching Wikileaf: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Wikileaf returned {response.status_code} for {strain_name}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = StrainData(
                name=strain_name,
                normalized_name=self.normalize_strain_name(strain_name),
                scraped_from=['Wikileaf']
            )
            
            # Extract strain type
            type_elem = soup.find('div', class_='strain-type')
            if type_elem:
                type_text = type_elem.get_text(strip=True).lower()
                if 'indica' in type_text:
                    data.strain_type = 'Indica'
                elif 'sativa' in type_text:
                    data.strain_type = 'Sativa'
                elif 'hybrid' in type_text:
                    data.strain_type = 'Hybrid'
            
            # Extract genetics
            genetics_section = soup.find('div', class_='genetics')
            if genetics_section:
                parent_text = genetics_section.get_text()
                # Look for "Parent1 x Parent2" pattern
                match = re.search(r'([A-Za-z0-9\s]+)\s*[xX×]\s*([A-Za-z0-9\s]+)', parent_text)
                if match:
                    data.parent1 = match.group(1).strip()
                    data.parent2 = match.group(2).strip()
            
            # Extract effects
            effects_section = soup.find('div', class_='effects')
            if effects_section:
                data.effects = [elem.get_text(strip=True) for elem in effects_section.find_all('li')]
            
            time.sleep(1)
            return data
            
        except Exception as e:
            logger.error(f"Error scraping Wikileaf for {strain_name}: {e}")
            return None
    
    def scrape_allbud(self, strain_name: str) -> Optional[StrainData]:
        """Scrape data from AllBud"""
        try:
            url_name = strain_name.lower().replace(' ', '-')
            url = f"https://www.allbud.com/marijuana-strains/info/{url_name}"
            
            logger.info(f"Fetching AllBud: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"AllBud returned {response.status_code} for {strain_name}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = StrainData(
                name=strain_name,
                normalized_name=self.normalize_strain_name(strain_name),
                scraped_from=['AllBud']
            )
            
            # Extract strain type
            type_badge = soup.find('span', class_='strain-badge')
            if type_badge:
                type_text = type_badge.get_text(strip=True).lower()
                if 'indica' in type_text:
                    data.strain_type = 'Indica'
                elif 'sativa' in type_text:
                    data.strain_type = 'Sativa'
                elif 'hybrid' in type_text:
                    data.strain_type = 'Hybrid'
            
            # Extract description
            desc_elem = soup.find('div', class_='strain-description')
            if desc_elem:
                data.description = desc_elem.get_text(strip=True)
            
            # Extract flavors
            flavor_tags = soup.find_all('a', class_='flavor-tag')
            if flavor_tags:
                data.flavor_profile = ', '.join([tag.get_text(strip=True) for tag in flavor_tags])
            
            time.sleep(1)
            return data
            
        except Exception as e:
            logger.error(f"Error scraping AllBud for {strain_name}: {e}")
            return None
    
    def build_lineage_tree(self, strain_name: str, max_depth: int = 3, current_depth: int = 0) -> Dict:
        """
        Recursively build lineage tree for a strain
        """
        if current_depth >= max_depth:
            return {"name": strain_name}
        
        strain_data = self.scrape_strain(strain_name)
        if not strain_data:
            return {"name": strain_name}
        
        tree = {
            "name": strain_data.name,
            "type": strain_data.strain_type,
            "parents": []
        }
        
        if strain_data.parent1:
            tree["parents"].append(
                self.build_lineage_tree(strain_data.parent1, max_depth, current_depth + 1)
            )
        
        if strain_data.parent2:
            tree["parents"].append(
                self.build_lineage_tree(strain_data.parent2, max_depth, current_depth + 1)
            )
        
        return tree


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python strain_scraper.py \"Strain Name\" [--build-tree]")
        print("\nExamples:")
        print("  python strain_scraper.py \"Jealousy\"")
        print("  python strain_scraper.py \"Grape Cream Cake\" --build-tree")
        sys.exit(1)
    
    strain_name = sys.argv[1]
    build_tree = "--build-tree" in sys.argv
    
    scraper = StrainScraper()
    
    if build_tree:
        print(f"\nBuilding lineage tree for: {strain_name}")
        tree = scraper.build_lineage_tree(strain_name)
        print(json.dumps(tree, indent=2))
    else:
        print(f"\nScraping data for: {strain_name}")
        data = scraper.scrape_strain(strain_name)
        
        if data:
            print("\n=== Strain Information ===")
            print(f"Name: {data.name}")
            print(f"Type: {data.strain_type}")
            
            if data.parent1 or data.parent2:
                print(f"\nLineage:")
                if data.parent1:
                    print(f"  Parent 1: {data.parent1}")
                if data.parent2:
                    print(f"  Parent 2: {data.parent2}")
            
            if data.description:
                print(f"\nDescription:\n{data.description}")
            
            if data.flavor_profile:
                print(f"\nFlavors: {data.flavor_profile}")
            
            if data.aroma_profile:
                print(f"Aromas: {data.aroma_profile}")
            
            if data.effects:
                print(f"\nEffects: {', '.join(data.effects)}")
            
            if data.primary_terpenes:
                print(f"\nPrimary Terpenes: {', '.join(data.primary_terpenes)}")
            
            print(f"\nData sources: {', '.join(data.scraped_from)}")
        else:
            print(f"Could not find strain data for: {strain_name}")


if __name__ == "__main__":
    main()
