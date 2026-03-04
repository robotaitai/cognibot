from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class PackageInfo(BaseModel):
    name: str
    path: str
    build_type: Optional[str] = None
    depends: List[str] = Field(default_factory=list)

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
