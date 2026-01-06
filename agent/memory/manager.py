"""
记忆模块
实现用户信息的存储、管理和读取
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MemoryType(Enum):
    """记忆类型"""
    USER_PREFERENCE = "user_preference"  # 用户偏好
    USER_INFO = "user_info"              # 用户基本信息
    TOPIC_INTEREST = "topic_interest"    # 话题兴趣
    INTERACTION = "interaction"          # 交互记录
    FACT = "fact"                        # 用户相关事实


@dataclass
class MemoryItem:
    """单条记忆"""
    id: str
    memory_type: MemoryType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5  # 重要性评分 0-1
    access_count: int = 0    # 访问次数
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["memory_type"] = self.memory_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryItem":
        data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)


class MemoryStorage(ABC):
    """记忆存储抽象基类"""
    
    @abstractmethod
    async def save(self, item: MemoryItem) -> bool:
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        pass
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        pass
    
    @abstractmethod
    async def get_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self) -> List[MemoryItem]:
        pass


class LocalFileStorage(MemoryStorage):
    """本地文件存储实现"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.memory_file = os.path.join(storage_path, "memories.json")
        self._ensure_storage_exists()
        self._cache: Dict[str, MemoryItem] = {}
        self._load_from_file()
    
    def _ensure_storage_exists(self):
        os.makedirs(self.storage_path, exist_ok=True)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
    
    def _load_from_file(self):
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache = {
                    k: MemoryItem.from_dict(v) for k, v in data.items()
                }
        except (json.JSONDecodeError, FileNotFoundError):
            self._cache = {}
    
    def _save_to_file(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            data = {k: v.to_dict() for k, v in self._cache.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def save(self, item: MemoryItem) -> bool:
        self._cache[item.id] = item
        self._save_to_file()
        return True
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        item = self._cache.get(memory_id)
        if item:
            item.access_count += 1
            self._save_to_file()
        return item
    
    async def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """简单的关键词搜索"""
        query_lower = query.lower()
        results = []
        
        for item in self._cache.values():
            score = 0
            content_lower = item.content.lower()
            
            # 计算匹配分数
            if query_lower in content_lower:
                score += 1.0
            
            # 关键词部分匹配
            for word in query_lower.split():
                if word in content_lower:
                    score += 0.3
            
            if score > 0:
                results.append((item, score * item.importance))
        
        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:top_k]]
    
    async def get_by_type(self, memory_type: MemoryType) -> List[MemoryItem]:
        return [
            item for item in self._cache.values() 
            if item.memory_type == memory_type
        ]
    
    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._cache:
            del self._cache[memory_id]
            self._save_to_file()
            return True
        return False
    
    async def list_all(self) -> List[MemoryItem]:
        return list(self._cache.values())


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self._id_counter = 0
    
    def _generate_id(self) -> str:
        self._id_counter += 1
        return f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._id_counter}"
    
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
    ) -> MemoryItem:
        """添加一条记忆"""
        item = MemoryItem(
            id=self._generate_id(),
            memory_type=memory_type,
            content=content,
            importance=importance,
            metadata=metadata or {},
        )
        await self.storage.save(item)
        return item
    
    async def recall(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """根据查询回忆相关记忆"""
        return await self.storage.search(query, top_k)
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """获取用户画像"""
        profile = {
            "preferences": [],
            "info": [],
            "interests": [],
            "facts": [],
        }
        
        # 获取各类型记忆
        prefs = await self.storage.get_by_type(MemoryType.USER_PREFERENCE)
        profile["preferences"] = [p.content for p in prefs]
        
        infos = await self.storage.get_by_type(MemoryType.USER_INFO)
        profile["info"] = [i.content for i in infos]
        
        interests = await self.storage.get_by_type(MemoryType.TOPIC_INTEREST)
        profile["interests"] = [i.content for i in interests]
        
        facts = await self.storage.get_by_type(MemoryType.FACT)
        profile["facts"] = [f.content for f in facts]
        
        return profile
    
    async def extract_and_save_memory(
        self,
        user_message: str,
        assistant_response: str,
        extracted_info: Optional[Dict] = None,
    ) -> List[MemoryItem]:
        """从对话中提取并保存记忆（需要LLM辅助提取）"""
        saved_items = []
        
        if extracted_info:
            for memory_type_str, contents in extracted_info.items():
                try:
                    memory_type = MemoryType(memory_type_str)
                    for content in contents:
                        item = await self.add_memory(
                            content=content,
                            memory_type=memory_type,
                            importance=0.6,
                            metadata={
                                "source_user_msg": user_message[:100],
                            }
                        )
                        saved_items.append(item)
                except ValueError:
                    continue
        
        return saved_items
    
    async def format_memories_for_context(self, query: str, max_items: int = 5) -> str:
        """将记忆格式化为上下文字符串"""
        memories = await self.recall(query, max_items)
        
        if not memories:
            return ""
        
        lines = ["[用户相关记忆]"]
        for mem in memories:
            lines.append(f"- [{mem.memory_type.value}] {mem.content}")
        
        return "\n".join(lines)


def create_memory_manager(storage_path: str) -> MemoryManager:
    """创建记忆管理器的工厂函数"""
    storage = LocalFileStorage(storage_path)
    return MemoryManager(storage)
