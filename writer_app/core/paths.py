from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    assets_dir: Path
    sample_data_dir: Path
    runtime_data_dir: Path
    legacy_data_dir: Path
    docs_dir: Path
    tools_dir: Path

    def ensure_layout(self) -> None:
        self.assets_dir.mkdir(exist_ok=True)
        self.sample_data_dir.mkdir(exist_ok=True)
        self.runtime_data_dir.mkdir(exist_ok=True)
        self.logs_dir().mkdir(parents=True, exist_ok=True)
        self.runtime_subdir("wiki_images").mkdir(parents=True, exist_ok=True)

    def logs_dir(self) -> Path:
        return self.runtime_data_dir / "logs"

    def runtime_subdir(self, *parts: str) -> Path:
        return self.runtime_data_dir.joinpath(*parts)

    def find_asset_dir(self, *parts: str, create_in_assets: bool = False) -> Path:
        candidates = [
            self.assets_dir.joinpath(*parts),
            self.legacy_data_dir.joinpath(*parts),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        target = self.assets_dir.joinpath(*parts)
        if create_in_assets:
            target.mkdir(parents=True, exist_ok=True)
        return target

    def find_asset_file(self, *parts: str) -> Path:
        for base in (self.assets_dir, self.legacy_data_dir):
            candidate = base.joinpath(*parts)
            if candidate.exists():
                return candidate
        return self.assets_dir.joinpath(*parts)

    def find_data_file(
        self,
        name: str,
        *,
        create_in: str = "runtime",
        include_assets: bool = False,
    ) -> Path:
        candidates = [self.runtime_data_dir / name, self.sample_data_dir / name]
        if include_assets:
            candidates.append(self.assets_dir / name)
        candidates.append(self.legacy_data_dir / name)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        targets = {
            "runtime": self.runtime_data_dir,
            "sample": self.sample_data_dir,
            "assets": self.assets_dir,
            "legacy": self.legacy_data_dir,
        }
        target_dir = targets.get(create_in, self.runtime_data_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / name

    def default_events_file(self) -> Path:
        return self.find_data_file("school_events.json", create_in="sample")

    def default_word_bank_file(self) -> Path:
        return self.find_data_file("word_bank.json", create_in="sample")

    def default_sample_project(self) -> Path:
        return self.find_data_file("1.writerproj", create_in="sample")

    def sound_base_dir(self) -> Path:
        sounds_dir = self.find_asset_dir("sounds")
        return sounds_dir.parent

    def fonts_dir(self) -> Path:
        return self.find_asset_dir("fonts", create_in_assets=True)

    def wiki_images_dir(self) -> Path:
        return self.runtime_subdir("wiki_images")


@lru_cache(maxsize=1)
def get_app_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[2]
    paths = AppPaths(
        repo_root=repo_root,
        assets_dir=repo_root / "assets",
        sample_data_dir=repo_root / "sample_data",
        runtime_data_dir=repo_root / "runtime_data",
        legacy_data_dir=repo_root / "writer_data",
        docs_dir=repo_root / "docs",
        tools_dir=repo_root / "tools",
    )
    paths.ensure_layout()
    return paths
