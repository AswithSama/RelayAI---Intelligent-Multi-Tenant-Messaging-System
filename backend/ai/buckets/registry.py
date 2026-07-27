"""ai/buckets/registry.py"""

from dataclasses import dataclass
from typing import Any, Callable, Literal

PromptType = str | Callable[[dict[str, Any]], str]
BucketLevel = Literal["broad", "sub"]


@dataclass(frozen=True)
class BucketConfig:
    name: str
    description: str
    level: BucketLevel = "broad"
    prompt: PromptType | None = None
    parent: str | None = None

    def get_prompt(self, state: dict[str, Any]) -> str:
        if self.prompt is None:
            return ""

        if callable(self.prompt):
            return self.prompt(state)

        return self.prompt


class BucketRegistry:
    def __init__(self):
        self._buckets: dict[str, BucketConfig] = {}

    def register(self, bucket: BucketConfig) -> None:
        if not bucket.name:
            raise ValueError("Bucket name is required.")

        if bucket.name in self._buckets:
            raise ValueError(f"Bucket already registered: {bucket.name}")

        if bucket.level == "broad" and bucket.parent:
            raise ValueError(f"Broad bucket should not have a parent: {bucket.name}")

        if bucket.level == "sub" and not bucket.parent:
            raise ValueError(f"Sub-bucket must have a parent: {bucket.name}")

        if bucket.level == "sub" and bucket.prompt is None:
            raise ValueError(f"Sub-bucket prompt is required: {bucket.name}")

        self._buckets[bucket.name] = bucket

    def register_many(self, buckets: list[BucketConfig]) -> None:
        for bucket in buckets:
            self.register(bucket)

    def get(self, name: str) -> BucketConfig:
        if name not in self._buckets:
            raise KeyError(f"Unknown bucket: {name}")
        return self._buckets[name]

    def exists(self, name: str) -> bool:
        return name in self._buckets

    def names(self) -> list[str]:
        return list(self._buckets)

    list_buckets = names

    def _filter(
        self,
        *,
        level: BucketLevel | None = None,
        parent: str | None = None,
    ) -> list[BucketConfig]:
        return [
            bucket
            for bucket in self._buckets.values()
            if (level is None or bucket.level == level)
            and (parent is None or bucket.parent == parent)
        ]

    def list_bucket_details(
        self,
        *,
        level: BucketLevel | None = None,
        parent: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": bucket.name,
                "description": bucket.description,
                "level": bucket.level,
                "parent": bucket.parent,
                "has_prompt": bucket.prompt is not None,
            }
            for bucket in self._filter(level=level, parent=parent)
        ]

    def list_names(
        self,
        *,
        level: BucketLevel | None = None,
        parent: str | None = None,
    ) -> list[str]:
        return [bucket.name for bucket in self._filter(level=level, parent=parent)]

    def get_many(self, names: list[str]) -> list[BucketConfig]:
        return [self.get(name) for name in names if self.exists(name)]

    def get_children(self, parent: str) -> list[BucketConfig]:
        return self._filter(parent=parent)
