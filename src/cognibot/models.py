from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class TopicInfo(BaseModel):
    topic: str
    msg_type: str
    direction: str  # "pub" or "sub"
    source_file: str
    node_class: Optional[str] = None


class ServiceInfo(BaseModel):
    service: str
    srv_type: str
    role: str  # "server" or "client"
    source_file: str
    node_class: Optional[str] = None


class PackageInfo(BaseModel):
    name: str
    path: str
    build_type: Optional[str] = None
    depends: List[str] = Field(default_factory=list)
    is_vendor: bool = False
    topics: List[TopicInfo] = Field(default_factory=list)
    services: List[ServiceInfo] = Field(default_factory=list)


class Snapshot(BaseModel):
    snapshot_id: str
    created_at: datetime
    repo_root: str
    git_commit: Optional[str] = None
    git_dirty: bool = False

    packages: List[PackageInfo] = Field(default_factory=list)
    launch_files: List[str] = Field(default_factory=list)
    param_files: List[str] = Field(default_factory=list)
    interfaces: Dict[str, List[str]] = Field(default_factory=lambda: {"msg": [], "srv": [], "action": []})
