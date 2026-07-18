from pathlib import Path
import tempfile
import unittest

from build_provenance import collect_build_provenance, public_build_provenance


class BuildProvenanceTests(unittest.TestCase):
    def test_build_id_changes_when_a_source_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "planner.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            first = collect_build_provenance({"burners": 2}, repo_root=root)
            source.write_text("VALUE = 2\n", encoding="utf-8")
            second = collect_build_provenance({"burners": 2}, repo_root=root)

        self.assertNotEqual(first["build_id"], second["build_id"])
        self.assertEqual(first["configuration"], {"burners": 2})

    def test_manifest_uses_relative_paths_and_short_hashes(self):
        provenance = collect_build_provenance()

        self.assertTrue(provenance["files"])
        self.assertTrue(all(not Path(item["path"]).is_absolute() for item in provenance["files"]))
        self.assertTrue(all(len(item["sha256"]) == 12 for item in provenance["files"]))

    def test_runtime_dependency_directories_are_never_fingerprinted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "planner.py").write_text("VALUE = 1\n", encoding="utf-8")
            dependency = root / ".venv" / "lib" / "python" / "site-packages"
            dependency.mkdir(parents=True)
            (dependency / "private_runtime.py").write_text("SECRET = True\n", encoding="utf-8")
            provenance = collect_build_provenance(repo_root=root)

        paths = [item["path"] for item in provenance["files"]]
        self.assertEqual(paths, ["planner.py"])
        self.assertFalse(any(".venv" in path or "site-packages" in path for path in paths))

    def test_public_provenance_omits_internal_file_manifest(self):
        detailed = collect_build_provenance({"internal": True})
        public = public_build_provenance(detailed, {"candidate_id": "meal-1"})

        self.assertNotIn("files", public)
        self.assertEqual(public["build_id"], detailed["build_id"])
        self.assertEqual(public["configuration"], {"candidate_id": "meal-1"})


if __name__ == "__main__":
    unittest.main()
