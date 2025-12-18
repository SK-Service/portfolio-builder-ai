from firebase_admin import firestore
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class FirestoreCache:
    """
    Firestore-based cache with TTL support.
    Survives cold starts, no Redis needed.
    Gracefully handles unavailable Firestore.
    """
    
    def __init__(self, collection_name: str = "agent_cache"):
        """
        Initialize Firestore cache.
        
        Args:
            collection_name: Firestore collection for cache storage
        """
        self.db = None
        self.collection = None
        self.cache_enabled = False
        
        try:
            self.db = firestore.client()
            self.collection = self.db.collection(collection_name)
            self.cache_enabled = True
            logger.info(f"Firestore cache initialized: {collection_name}")
        except Exception as e:
            logger.warning(f"Firestore cache unavailable: {e}")
            logger.warning("Cache operations will be disabled (all requests will fetch fresh data)")
            self.cache_enabled = False
    
    def _generate_cache_key(self, **kwargs) -> str:
        """
        Generate deterministic cache key from parameters.
        
        Args:
            **kwargs: Parameters to hash
            
        Returns:
            SHA256 hash as cache key
        """
        key_string = json.dumps(kwargs, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, ttl_hours: int = 1, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get cached data if exists and not expired.
        
        Args:
            ttl_hours: Time-to-live in hours
            **kwargs: Cache key parameters
            
        Returns:
            Cached data dict or None if miss/expired
        """
        if not self.cache_enabled:
            logger.debug("Cache disabled, returning None")
            return None
        
        try:
            cache_key = self._generate_cache_key(**kwargs)
            doc_ref = self.collection.document(cache_key)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.debug(f"Cache miss: {cache_key[:8]}...")
                return None
            
            data = doc.to_dict()
            cached_at = data.get('cached_at')
            
            if not cached_at:
                logger.warning(f"Cache entry missing timestamp: {cache_key[:8]}...")
                return None
            
            expiry = cached_at + timedelta(hours=ttl_hours)
            now = datetime.now(timezone.utc)
            
            if now > expiry:
                age_hours = (now - cached_at).total_seconds() / 3600
                logger.info(f"Cache expired (age: {age_hours:.1f}h): {cache_key[:8]}...")
                return None
            
            logger.info(f"Cache hit: {cache_key[:8]}...")
            return data.get('value')
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, value: Dict[str, Any], **kwargs) -> bool:
        """
        Store data in cache with timestamp.
        
        Args:
            value: Data to cache
            **kwargs: Cache key parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.cache_enabled:
            logger.debug("Cache disabled, skipping set")
            return False
        
        try:
            cache_key = self._generate_cache_key(**kwargs)
            doc_ref = self.collection.document(cache_key)
            
            cache_entry = {
                'value': value,
                'cached_at': datetime.now(timezone.utc),
                'key_params': kwargs
            }
            
            doc_ref.set(cache_entry)
            logger.info(f"Cache set: {cache_key[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def get_stale(self, max_age_hours: int = 24, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get cached data even if expired (for fallback scenarios).
        
        Args:
            max_age_hours: Maximum acceptable age (default 24h)
            **kwargs: Cache key parameters
            
        Returns:
            Cached data dict with staleness info, or None if too old
        """
        if not self.cache_enabled:
            logger.debug("Cache disabled, returning None")
            return None
        
        try:
            cache_key = self._generate_cache_key(**kwargs)
            doc_ref = self.collection.document(cache_key)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            cached_at = data.get('cached_at')
            
            if not cached_at:
                return None
            
            age = datetime.now(timezone.utc) - cached_at
            age_hours = age.total_seconds() / 3600
            
            if age_hours > max_age_hours:
                logger.warning(f"Cache too old ({age_hours:.1f}h): {cache_key[:8]}...")
                return None
            
            result = data.get('value', {})
            result['_cache_metadata'] = {
                'is_stale': True,
                'age_hours': round(age_hours, 1),
                'cached_at': cached_at.isoformat()
            }
            
            logger.info(f"Returning stale cache ({age_hours:.1f}h old): {cache_key[:8]}...")
            return result
            
        except Exception as e:
            logger.error(f"Stale cache get error: {e}")
            return None