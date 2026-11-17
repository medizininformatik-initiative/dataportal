#!/usr/bin/env python3
"""Generate test data and CRTDLs that cover every DSE profile and field of an ontology release.

Inputs (downloaded once into --cache-dir):
  fhir-ontology-generator release assets backend.zip (DSE profile tree) and dse_structures.zip
  (StructureDefinitions, the same set TORCH loads), plus the FHIR R4 core package for base
  datatypes and core value sets.

Outputs in --out-dir:
  crtdls/<module>--<profile>.json   one CRTDL per DSE profile. Cohort: all male and female patients.
                                    The profile's group selects every DSE field id and every reference
                                    field. Each reference field links to one of its target profiles.
  testdata/ontology-testdata.json   FHIR transaction bundle (PUT) with resources for every profile.
                                    Each profile gets one variant per type of its widest choice element.
  coverage.md, coverage.json        DSE field ids and reference fields that no generated resource fills

Usage:
  ./generate-ontology-tests.py [--release v5.2.1] [--upload]
  ./run-dup-pipeline-tests.py --crtdl-dir ontology-tests/crtdls
"""
import argparse
import copy
import hashlib
import io
import json
import re
import ssl
import subprocess
import sys
import tarfile
import urllib.request
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE_DIR = HERE.parent
RELEASE_URL = "https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/{tag}/{asset}"
R4_CORE_URL = "https://packages.fhir.org/hl7.fhir.r4.core/4.0.1"
# Patient group of every CRTDL. The example DUP pipeline enriches CRTDLs with this group, and TORCH allows one
# Patient group, so it must be this profile. Every generated patient claims it.
PATIENT_GROUP = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
NS = uuid.UUID("6f1c3a52-6d1e-4c41-9a51-0d2b7c1e9a10")
MAX_VARIANTS = 12
MAX_TYPE_DEPTH = 4
SKIP_CHILDREN = {"id", "meta", "implicitRules", "contained"}
DIV = '<div xmlns="http://www.w3.org/1999/xhtml"><p>test</p></div>'
PRIMITIVES = {
    "boolean": True, "integer": 1, "positiveInt": 1, "unsignedInt": 1, "decimal": 1.5,
    "string": "test", "markdown": "test", "id": "test-id", "code": "test",
    "uri": "http://example.org/fhir/test", "url": "http://example.org/fhir/test",
    "canonical": "http://example.org/fhir/StructureDefinition/test", "oid": "urn:oid:1.2.276.0.76.4.17",
    "uuid": "urn:uuid:" + str(uuid.uuid5(NS, "test")), "date": "2024-01-15",
    "dateTime": "2024-01-15T10:00:00+01:00", "instant": "2024-01-15T10:00:00.000+01:00",
    "time": "10:00:00", "base64Binary": "dGVzdA==", "xhtml": DIV,
}
NAME_HINTS = {"contentType": "text/plain", "language": "de"}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--release", default="v5.2.2", help="fhir-ontology-generator release tag")
    p.add_argument("--cache-dir", type=Path, default=HERE / ".cache")
    p.add_argument("--out-dir", type=Path, default=HERE / "ontology-tests")
    p.add_argument("--cohort", type=Path, default=HERE / "replacement-cohort.json")
    p.add_argument("--upload", action="store_true", help="POST the bundle to --fhir-url")
    p.add_argument("--fhir-url", default="https://fhir.localhost:444/fhir")
    return p.parse_args()


# ---------------------------------------------------------------- inputs

def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        print(f"downloading {url}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        with urllib.request.urlopen(url) as r, tmp.open("wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    return dest


def load_dse_profiles(backend_zip: Path) -> list:
    with zipfile.ZipFile(backend_zip) as z:
        name = next(n for n in z.namelist() if n.endswith("R__load_latest_dse_profiles.sql"))
        text = z.read(name).decode("utf-8")
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\((\d+),'((?:[^']|'')*)','((?:[^']|'')*)'\)[,;]?\s*$", line)
        if m:
            rows.append(json.loads(m[3].replace("''", "'")))
    if not rows:
        sys.exit(f"no DSE profiles found in {backend_zip}")
    return rows


def load_zip_json(path: Path) -> list:
    with zipfile.ZipFile(path) as z:
        return [json.loads(z.read(n)) for n in z.namelist() if n.endswith(".json")]


def load_r4_core(path: Path) -> list:
    out = []
    with tarfile.open(path) as t:
        for m in t.getmembers():
            base = m.name.rsplit("/", 1)[-1]
            if m.isfile() and base.startswith(("StructureDefinition-", "ValueSet-", "CodeSystem-")):
                out.append(json.load(t.extractfile(m)))
    return out


# ---------------------------------------------------------------- terminology

class Terminology:
    def __init__(self, resources):
        self.vs = {r["url"]: r for r in resources if r["resourceType"] == "ValueSet"}
        self.cs = {r["url"]: r for r in resources if r["resourceType"] == "CodeSystem"}
        self.cache = {}

    def first_code(self, vs_url):
        """(system, code, display) of the first selectable concept of a value set, or None."""
        vs_url = (vs_url or "").split("|")[0]
        if vs_url not in self.cache:
            self.cache[vs_url] = None
            self.cache[vs_url] = self._resolve(vs_url)
        return self.cache[vs_url]

    def _resolve(self, vs_url):
        vs = self.vs.get(vs_url)
        if not vs:
            return None
        for c in vs.get("expansion", {}).get("contains", []):
            if c.get("code") and not c.get("abstract"):
                return c.get("system"), c["code"], c.get("display")
        for inc in vs.get("compose", {}).get("include", []):
            system = inc.get("system")
            if inc.get("concept"):
                c = inc["concept"][0]
                return system, c["code"], c.get("display")
            if system and not inc.get("filter"):
                c = self._first_concept(self.cs.get(system, {}).get("concept", []))
                if c:
                    return system, c["code"], c.get("display")
            for sub in inc.get("valueSet", []):
                if r := self.first_code(sub):
                    return r
        return None

    def _first_concept(self, concepts):
        for c in concepts:
            props = {p.get("code"): p.get("valueBoolean", p.get("valueCode")) for p in c.get("property", [])}
            if props.get("notSelectable") is True or props.get("abstract") is True or props.get("status") == "deprecated":
                if r := self._first_concept(c.get("concept", [])):
                    return r
                continue
            return c
        return None


# ---------------------------------------------------------------- structure definitions

class Snapshot:
    def __init__(self, sd):
        self.url, self.type = sd["url"], sd["type"]
        elements = sd["snapshot"]["element"]
        self.root = elements[0]["id"]
        self.el = {e["id"]: e for e in elements}
        self.children = defaultdict(list)
        self.slices = defaultdict(list)
        for e in elements[1:]:
            eid = e["id"]
            head, last = eid.rsplit(".", 1)
            if "/" in last:
                continue  # re-slices
            if ":" in last:
                self.slices[f"{head}.{last.split(':')[0]}"].append(eid)
            else:
                self.children[head].append(eid)


def short_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fixed_or_pattern(e):
    fixed = next((v for k, v in e.items() if k.startswith("fixed")), None)
    pattern = next((v for k, v in e.items() if k.startswith("pattern")), None)
    return fixed, pattern


def merge_pattern(value, pattern):
    """Return value with pattern applied. Pattern values win. List items from the pattern must be present."""
    if not isinstance(pattern, (dict, list)) or value is None:
        return copy.deepcopy(pattern)
    if isinstance(pattern, list):
        value = list(value) if isinstance(value, list) else [value]
        for p in pattern:
            if not any(matches(v, p) for v in value):
                if value and isinstance(value[0], dict) and isinstance(p, dict):
                    value[0] = merge_pattern(value[0], p)
                else:
                    value.append(copy.deepcopy(p))
        return value
    if not isinstance(value, dict):
        return copy.deepcopy(pattern)
    out = dict(value)
    for k, p in pattern.items():
        out[k] = merge_pattern(out.get(k), p) if k in out else copy.deepcopy(p)
    return out


def matches(value, pattern):
    if isinstance(pattern, dict):
        return isinstance(value, dict) and all(matches(value.get(k), p) for k, p in pattern.items())
    if isinstance(pattern, list):
        return isinstance(value, list) and all(any(matches(v, p) for v in value) for p in pattern)
    return value == pattern


def unsliced_ids(eid):
    """eid and every id obtained by dropping slice names. An instance of a slice is also an instance of its base."""
    parts = eid.split(".")
    sliced = [i for i, p in enumerate(parts) if ":" in p]
    out = []
    for mask in range(1 << len(sliced)):
        q = list(parts)
        for b, i in enumerate(sliced):
            if mask >> b & 1:
                q[i] = q[i].split(":")[0]
        out.append(".".join(q))
    return out


class Ctx:
    def __init__(self, snap, variant, patient_ref, forced):
        self.snap, self.variant, self.patient_ref, self.forced = snap, variant, patient_ref, forced
        self.covered = set()
        self.aliases = []  # (contentReference target, element id) while generating a contentReference

    def unalias(self, eid):
        for src, dst in reversed(self.aliases):
            if eid == src or eid.startswith(src + "."):
                eid = dst + eid[len(src):]
        return eid

    def cover(self, snap, eid):
        if snap is self.snap:
            self.covered.update(unsliced_ids(self.unalias(eid)))

    def forced_target(self, snap, eid):
        if snap is not self.snap:
            return None
        return next((self.forced[i] for i in unsliced_ids(self.unalias(eid)) if i in self.forced), None)


class Generator:
    def __init__(self, sds, core_sds, term, dse_urls):
        self.sds = {**{sd["url"]: sd for sd in core_sds}, **{sd["url"]: sd for sd in sds}}
        self.core_types = {sd["type"]: sd for sd in core_sds
                           if sd.get("derivation") == "specialization" or sd.get("kind") == "primitive-type"
                           or sd["url"] == f"http://hl7.org/fhir/StructureDefinition/{sd['type']}"}
        self.term = term
        self.dse_urls = dse_urls
        self.snaps = {}
        self.stubs = {}
        self.issues = set()

    def snap(self, url_or_sd):
        sd = self.sds.get(url_or_sd) if isinstance(url_or_sd, str) else url_or_sd
        if sd is None or "snapshot" not in sd:
            return None
        if sd["url"] not in self.snaps:
            self.snaps[sd["url"]] = Snapshot(sd)
        return self.snaps[sd["url"]]

    def resource_type(self, profile_url):
        sd = self.sds.get((profile_url or "").split("|")[0])
        if sd:
            return sd["type"]
        # profile not in the release: use the last URL segment if it names a resource type
        last = (profile_url or "").split("|")[0].rsplit("/", 1)[-1]
        sd = self.core_types.get(last)
        return last if sd and sd.get("kind") == "resource" else None

    @staticmethod
    def resource_id(profile_url, variant):
        return f"ot-{short_id(profile_url)}-{variant}"

    def variants(self, url):
        snap = self.snap(url)
        n = 1
        for eid, e in snap.el.items():
            if e.get("max") == "0":
                continue
            if eid.endswith("[x]"):
                codes = {t["code"] for t in e.get("type", [])}
                codes |= {t["code"] for s in snap.slices.get(eid, []) for t in snap.el[s].get("type", [])}
                n = max(n, len(codes))
            if e.get("max") == "1" and snap.slices.get(eid):
                n = max(n, len(snap.slices[eid]))
        return min(n, MAX_VARIANTS)

    # -- resources

    def resource(self, url, variant, patient_ref, forced):
        snap = self.snap(url)
        ctx = Ctx(snap, variant, patient_ref, forced)
        res = {"resourceType": snap.type, "id": self.resource_id(url, variant), "meta": {"profile": [url]}}
        res.update(self.children(snap, snap.root, ctx, 0))
        return res, ctx.covered

    def children(self, snap, node, ctx, depth):
        out = {}
        for cid in snap.children.get(node, []):
            name = cid.rsplit(".", 1)[1]
            if name in SKIP_CHILDREN or (depth > 0 and name == "extension" and not snap.slices.get(cid)):
                continue
            out.update(self.element(snap, cid, ctx, depth))
        if node != snap.root and self.missing_required(snap, node, out):
            return {}  # incomplete objects break strict parsers (DIMP), so leave the element out
        return out

    @staticmethod
    def missing_required(snap, node, out):
        for cid in snap.children.get(node, []):
            e, name = snap.el[cid], cid.rsplit(".", 1)[1]
            if e.get("min", 0) >= 1 and e.get("max") != "0" and name not in SKIP_CHILDREN:
                prefix = name[:-3] if name.endswith("[x]") else None
                if not any(k == name or k == "_" + name or (prefix and k.startswith(prefix)) for k in out):
                    return True
        return False

    def element(self, snap, eid, ctx, depth):
        """JSON members for one element: {name: value} plus {_name: extensions} for primitives."""
        e = snap.el[eid]
        if e.get("max") == "0":
            return {}
        name = eid.rsplit(".", 1)[1]
        is_list = e.get("base", {}).get("max", e.get("max")) != "1"
        if name.endswith("[x]"):
            return self.choice(snap, eid, name, ctx, depth)
        slices = [s for s in snap.slices.get(eid, []) if snap.el[s].get("max") != "0"]
        if slices:
            limit = len(slices) if e.get("max") in ("*", None) else min(len(slices), int(e["max"]))
            start = ctx.variant % len(slices)
            nodes = (slices[start:] + slices[:start])[:limit]
        elif name in ("extension", "modifierExtension"):
            return {}
        else:
            nodes = [eid]
        values, exts = [], []
        for node in nodes:
            v = self.value(snap, node, self.first_type(snap, node), ctx, depth)
            if v is None:
                continue
            v, ext = self.with_extensions(snap, [node], v, ctx, depth)
            values.append(v)
            exts.append(ext)
            ctx.cover(snap, node)
        if not values:
            return {}
        ctx.cover(snap, eid)
        out = {name: values if is_list else values[0]}
        if any(exts):
            out["_" + name] = exts if is_list else exts[0]
        return out

    def with_extensions(self, snap, nodes, value, ctx, depth):
        """Add the sliced extensions defined on nodes. Primitives get them as a separate _name object."""
        if isinstance(value, dict) and "extension" in value:
            return value, None
        for n in nodes:
            if snap.slices.get(f"{n}.extension"):
                ext = self.element(snap, f"{n}.extension", ctx, depth).get("extension")
                if ext:
                    if isinstance(value, dict):
                        return {**value, "extension": ext}, None
                    return value, {"extension": ext}
        return value, None

    def first_type(self, snap, eid):
        e = snap.el[eid]
        if e.get("type"):
            return e["type"][0]
        if e.get("contentReference"):
            return {"code": "#content", "ref": e["contentReference"].split("#", 1)[1]}
        return None

    def choice(self, snap, eid, name, ctx, depth):
        types = list(snap.el[eid].get("type", []))
        slices = [s for s in snap.slices.get(eid, []) if snap.el[s].get("max") != "0"]
        # type slices whose type the element does not allow (profile inconsistency) still get test data
        for s in slices:
            for t in snap.el[s].get("type", []):
                if t["code"] not in {x["code"] for x in types}:
                    types.append(t)
        if not types:
            return {}
        t = types[ctx.variant % len(types)]
        key = name[:-3] + t["code"][0].upper() + t["code"][1:]
        node = eid if len(types) == 1 else None
        for s in slices:
            if s.rsplit(":", 1)[1] == key:
                node = s
        v = self.value(snap, node, t, ctx, depth, base_eid=eid) if node else self.value_of_type(t, eid, ctx, depth, snap)
        if v is None:
            return {}
        v, ext = self.with_extensions(snap, [node, eid] if node else [eid], v, ctx, depth)
        ctx.cover(snap, eid)
        if node:
            ctx.cover(snap, node)
        return {key: v, **({"_" + key: ext} if ext else {})}

    def value(self, snap, node, t, ctx, depth, base_eid=None):
        if t is None:
            return None
        e = snap.el[node]
        fixed, pattern = fixed_or_pattern(e)
        code = t["code"]
        if code in PRIMITIVES and isinstance(fixed if fixed is not None else pattern, (dict, list)):
            self.issues.add(f"{snap.url}: {node} has type {code} but a complex fixed/pattern value. "
                            "Used its first code.")
            fixed = next(iter(re.findall(r'"code": "([^"]+)"', json.dumps(fixed or pattern))), PRIMITIVES[code])
            pattern = None
        if fixed is not None:
            return copy.deepcopy(fixed)
        if code == "#content":
            if ctx.aliases or depth >= MAX_TYPE_DEPTH:  # expand recursive structures one level only
                return None
            ctx.aliases.append((t["ref"], ctx.unalias(node)))
            obj = self.children(snap, t["ref"], ctx, depth + 2) or None
            ctx.aliases.pop()
        elif code == "Reference":
            obj = self.reference(t, ctx, self.target(snap, base_eid or node, t, ctx))
        elif code in PRIMITIVES or code.startswith("http://hl7.org/fhirpath/"):
            obj = self.primitive(code, e, node)
        elif code == "Narrative":
            obj = {"status": "generated", "div": DIV}
            for c in snap.children.get(node, []):
                ctx.cover(snap, c)
        elif code == "Resource":
            obj = {"resourceType": "Basic", "code": {"text": "test"}}
        elif snap.children.get(node):
            obj = self.children(snap, node, ctx, depth) or None
            if code == "Extension":
                obj = self.extension_url(obj, t, node)
        else:
            obj = self.value_of_type(t, node, ctx, depth, snap)
            self.cover_tree(snap, node, obj, ctx)
        if obj is not None and code in ("Coding", "CodeableConcept", "Quantity"):
            obj = self.bind(obj, code, e)
        if pattern is not None:
            obj = merge_pattern(obj, pattern)
        return obj

    def cover_tree(self, snap, node, obj, ctx):
        """Mark snapshot descendants of node that a value generated from a core type definition filled."""
        kids = snap.children.get(node) or snap.children.get(unsliced_ids(node)[-1], [])
        for c in kids:
            name = c.rsplit(".", 1)[1]
            items = obj.get(name) if isinstance(obj, dict) else None
            for item in items if isinstance(items, list) else [items] if items is not None else []:
                ctx.cover(snap, c)
                self.cover_tree(snap, c, item, ctx)

    def value_of_type(self, t, node, ctx, depth, snap=None):
        """Value of a complex type from its profile or core definition, for elements the snapshot does not expand."""
        code = t["code"]
        if code == "Reference":
            return self.reference(t, ctx, self.target(snap or ctx.snap, node, t, ctx))
        if code in PRIMITIVES:
            return PRIMITIVES[code]
        if code == "Narrative":
            return {"status": "generated", "div": DIV}
        prof = (t.get("profile") or [None])[0]
        sd = self.sds.get(prof) if prof else None
        if code == "Extension" and prof and not sd:
            return {"url": prof, "valueString": "test"}
        sd = sd or self.core_types.get(code)
        s2 = self.snap(sd) if sd else None
        if s2 is None or depth >= MAX_TYPE_DEPTH:
            return None
        obj = self.children(s2, s2.root, ctx, depth + 1) or None
        if sd.get("kind") == "resource":
            obj = {"resourceType": sd["type"], "id": f"ot-inline-{short_id(node)}", **(obj or {})}
        if code == "Extension":
            obj = self.extension_url(obj, t, node)
        if obj is not None and code in ("Coding", "CodeableConcept", "Quantity") and snap is not None:
            obj = self.bind(obj, code, snap.el[node])
        return obj

    @staticmethod
    def extension_url(obj, t, node):
        obj = obj or {}
        prof = (t.get("profile") or [None])[0]
        # url is a fhirpath System.String in the snapshot, so an unfixed url gets the string default
        if "url" not in obj or obj["url"] in (PRIMITIVES["uri"], PRIMITIVES["string"]):
            obj["url"] = prof or node.rsplit(":", 1)[-1]
        # ext-1: an extension has sub-extensions or a value, never both. Snapshots of complex
        # extensions do not always restrict value[x] to max 0, so drop the value here.
        if obj.get("extension"):
            for k in [k for k in obj if k.startswith(("value", "_value"))]:
                del obj[k]
        if len(obj) == 1:
            obj["valueString"] = "test"
        return {"url": obj.pop("url"), **obj}

    def primitive(self, code, e, node):
        code = {"http://hl7.org/fhirpath/System.String": "string"}.get(code, code)
        if code.startswith("http://hl7.org/fhirpath/"):
            return None
        name = node.rsplit(".", 1)[-1].split(":")[0]
        if name in NAME_HINTS:
            return NAME_HINTS[name]
        value = PRIMITIVES[code]
        if code == "code":
            b = self.code_from_binding(e)
            if b:
                value = b[1]
            elif self.binding(e).get("strength") == "required":
                self.issues.add(f"no code found for required binding {self.binding(e).get('valueSet')} "
                                f"of {e.get('base', {}).get('path', node)}. Used 'test'.")
        if isinstance(value, str) and e.get("maxLength"):
            value = value[: e["maxLength"]]
        return value

    def binding(self, e):
        """Binding of an element, or of its base element in the core definition if the profile has none."""
        if e.get("binding", {}).get("valueSet"):
            return e["binding"]
        return self.core_element(e).get("binding", {})

    def core_element(self, e):
        path = e.get("base", {}).get("path", e.get("path", ""))
        root = path.split(".")[0]
        snap = self.snap(self.core_types[root]) if root in self.core_types else None
        return next((x for x in snap.el.values() if x.get("path") == path), {}) if snap else {}

    def code_from_binding(self, e):
        """First code of the profile binding. Falls back to the core binding (MII value sets are not packaged)."""
        return (self.term.first_code(e.get("binding", {}).get("valueSet"))
                or self.term.first_code(self.core_element(e).get("binding", {}).get("valueSet")))

    def bind(self, obj, code, e):
        """Put a code from the element's binding into codings that still have the placeholder system.
        Codings with a system from a fixed or pattern value (slices) are left unchanged."""
        b = self.term.first_code(e.get("binding", {}).get("valueSet"))
        if not b:
            return obj
        coding = {k: v for k, v in zip(("system", "code", "display"), b) if v}
        placeholder = lambda c: c.get("system") in (None, PRIMITIVES["uri"])
        if code == "Coding":
            return {**obj, **coding} if placeholder(obj) else obj
        if code == "Quantity":
            return {**obj, "system": coding.get("system", obj.get("system")), "code": coding["code"]} if placeholder(obj) else obj
        codings = obj.get("coding") or [{}]
        if not all(placeholder(c) for c in codings):
            return obj
        return {**obj, "coding": [{**codings[0], **coding}] + codings[1:]}

    def target(self, snap, eid, t, ctx):
        """Target profile of a reference. Root-level subject and patient always point to the patient:
        TORCH links them to the Patient group, while the DSE offers only other targets for some of them."""
        root_field = snap is ctx.snap and eid.count(".") == 1 and eid.split(".")[1] in ("subject", "patient")
        if root_field and any(self.resource_type(p.split("|")[0]) == "Patient" for p in t.get("targetProfile", [])):
            return "Patient"
        return ctx.forced_target(snap, eid)

    def reference(self, t, ctx, target):
        if target is None:
            tps = [p.split("|")[0] for p in t.get("targetProfile", [])] or ["http://hl7.org/fhir/StructureDefinition/Resource"]
            types = [self.resource_type(p) for p in tps]
            if "Patient" in types or "Resource" in types:
                target = "Patient"
            else:
                target = next((p for p in tps if p in self.dse_urls), tps[0])
        if target == "Patient" or self.resource_type(target) == "Patient":
            return {"reference": ctx.patient_ref}
        if target in self.dse_urls:
            return {"reference": f"{self.resource_type(target)}/{self.resource_id(target, 0)}"}
        rt = self.resource_type(target) or "Basic"
        stub = self.stubs.setdefault(rt, {"resourceType": rt, "id": f"ot-stub-{rt.lower()}"})
        return {"reference": f"{rt}/{stub['id']}"}


# ---------------------------------------------------------------- DSE helpers

def field_ids(fields):
    for f in fields:
        yield f["id"]
        yield from field_ids(f.get("children", []))


def chosen_targets(entry, dse_urls):
    """One target profile per reference field: the first referenced profile that is a DSE profile."""
    out = {}
    for ref in entry.get("references", []):
        urls = [p["url"] for p in ref.get("referencedProfiles", []) if p.get("url") in dse_urls]
        if urls:
            out[ref["id"]] = urls[0]
    return out


def first_attribute(entry):
    """Minimal DSE attribute for groups that only need to exist: the first top-level non-reference field."""
    return [{"attributeRef": entry["fields"][0]["id"], "mustHave": False}]


def build_crtdl(entry, targets, gen, cohort, patient_url, by_url):
    url = entry["url"]
    gid = lambda key: str(uuid.uuid5(NS, f"{url}|{key}"))
    is_patient = gen.resource_type(url) == "Patient"
    patient_gid = gid("main") if is_patient else gid("patient")
    groups = {}
    if not is_patient:
        groups[patient_gid] = {"attributes": first_attribute(by_url[patient_url]), "id": patient_gid, "groupReference": patient_url, "name": "patient"}
    main = {"attributes": [{"attributeRef": i, "mustHave": False} for i in field_ids(entry["fields"])],
            "id": gid("main"), "groupReference": url, "name": slug(url.rsplit("/", 1)[1])}
    groups[main["id"]] = main
    for ref in entry.get("references", []):
        target = targets.get(ref["id"])
        if target is None:
            continue
        if gen.resource_type(target) == "Patient":
            linked = patient_gid
        elif target == url:
            linked = main["id"]
        else:
            linked = gid(target)
            groups.setdefault(linked, {"attributes": first_attribute(by_url[target]), "id": linked, "groupReference": target,
                                       "includeReferenceOnly": True,
                                       "name": "linked-" + slug(target.rsplit("/", 1)[1])})
        main["attributes"].append({"attributeRef": ref["id"], "mustHave": False, "linkedGroups": [linked]})
    return {"version": "http://json-schema.org/to-be-done/schema#", "display": f"Ontology test {url}",
            "cohortDefinition": cohort, "dataExtraction": {"attributeGroups": list(groups.values())}}


# ---------------------------------------------------------------- main

def upload(bundle_path: Path, fhir_url: str):
    token = subprocess.run(["bash", str(NODE_DIR / "get-fhir-server-access-token.sh")],
                           capture_output=True, text=True, check=True).stdout.strip()
    ssl_ctx = ssl.create_default_context(cafile=str(NODE_DIR / "auth" / "cert.pem"))
    req = urllib.request.Request(fhir_url, data=bundle_path.read_bytes(), method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/fhir+json",
                                          "Prefer": "return=minimal"})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=600) as r:
            print(f"uploaded {bundle_path.name}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        sys.exit(f"upload failed: HTTP {e.code}: {e.read().decode(errors='replace')[:4000]}")


def write_coverage(out: Path, coverage: list, issues: set):
    (out / "coverage.json").write_text(json.dumps({"profiles": coverage, "profile_issues": sorted(issues)}, indent=2))
    fields = sum(c["fields"] for c in coverage)
    missing = sum(len(c["uncovered_fields"]) for c in coverage)
    refs = sum(c["references"] for c in coverage)
    refs_missing = sum(len(c["uncovered_references"]) + len(c["unlinked_references"]) for c in coverage)
    lines = ["# Ontology test data coverage", "",
             f"Profiles: {len(coverage)}. Fields covered: {fields - missing} of {fields}. "
             f"Reference fields covered and linked: {refs - refs_missing} of {refs}.", "",
             "| Profile | Variants | Fields | Uncovered fields | Uncovered or unlinked references |",
             "| --- | --- | --- | --- | --- |"]
    for c in coverage:
        if c["uncovered_fields"] or c["uncovered_references"] or c["unlinked_references"]:
            refs_txt = ", ".join(c["uncovered_references"] + [f"{r} (no DSE target)" for r in c["unlinked_references"]])
            lines.append(f"| {c['crtdl']} | {c['variants']} | {c['fields']} | "
                         f"{', '.join(c['uncovered_fields']) or '-'} | {refs_txt or '-'} |")
    lines += ["", "## Profile issues", ""] + [f"- {i}" for i in sorted(issues)]
    (out / "coverage.md").write_text("\n".join(lines) + "\n")
    print(f"fields covered {fields - missing}/{fields}, references {refs - refs_missing}/{refs}")


def main():
    args = parse_args()
    cache = args.cache_dir / args.release
    backend = fetch(RELEASE_URL.format(tag=args.release, asset="backend.zip"), cache / "backend.zip")
    structures = fetch(RELEASE_URL.format(tag=args.release, asset="dse_structures.zip"), cache / "dse_structures.zip")
    core_pkg = fetch(R4_CORE_URL, args.cache_dir / "hl7.fhir.r4.core-4.0.1.tgz")

    entries = sorted(load_dse_profiles(backend), key=lambda e: e["url"])
    sds = load_zip_json(structures)
    core = load_r4_core(core_pkg)
    term = Terminology(core)
    core_sds = [r for r in core if r["resourceType"] == "StructureDefinition"]
    dse_urls = {e["url"] for e in entries}
    by_url = {e["url"]: e for e in entries}
    gen = Generator(sds, core_sds, term, dse_urls)
    if missing := [u for u in dse_urls if gen.snap(u) is None]:
        sys.exit(f"no StructureDefinition snapshot for {missing}")
    cohort = json.loads(args.cohort.read_text())

    patient_urls = sorted(u for u in dse_urls if gen.resource_type(u) == "Patient")
    if PATIENT_GROUP not in patient_urls:
        sys.exit(f"{PATIENT_GROUP} is not a DSE profile in {args.release}")
    patient_refs = [(u, k) for u in patient_urls for k in range(gen.variants(u))]

    resources, coverage = [], []
    crtdl_dir = args.out_dir / "crtdls"
    crtdl_dir.mkdir(parents=True, exist_ok=True)
    for old in crtdl_dir.glob("*.json"):
        old.unlink()
    for n, entry in enumerate(entries):
        url = entry["url"]
        targets = chosen_targets(entry, dse_urls)
        covered = set()
        nvar = gen.variants(url)
        for k in range(nvar):
            if gen.resource_type(url) == "Patient":
                i = patient_refs.index((url, k))
                pref = f"Patient/{gen.resource_id(url, k)}"
            else:
                # one patient for all other resources: TORCH resolves references within a patient's compartment
                i = 0
                pref = f"Patient/{gen.resource_id(PATIENT_GROUP, 0)}"
            res, cov = gen.resource(url, k, pref, targets)
            if res["resourceType"] == "Patient":
                res["gender"] = ("male", "female")[i % 2]
                if url != PATIENT_GROUP:
                    res["meta"]["profile"].append(PATIENT_GROUP)
            resources.append(res)
            covered |= cov

        name = f"{slug(entry['module']['original'])}--{slug(url.rsplit('/', 1)[1])}"
        crtdl = build_crtdl(entry, targets, gen, cohort, PATIENT_GROUP, by_url)
        fids = list(field_ids(entry["fields"]))
        refs = [r["id"] for r in entry.get("references", [])]
        dse_ids = {g["groupReference"]: set(field_ids(by_url[g["groupReference"]]["fields"]))
                   for g in crtdl["dataExtraction"]["attributeGroups"]}
        dse_ids[url] = set(fids) | set(refs)
        for g in crtdl["dataExtraction"]["attributeGroups"]:
            if bad := [a["attributeRef"] for a in g["attributes"] if a["attributeRef"] not in dse_ids[g["groupReference"]]]:
                sys.exit(f"{name}: attributes not in DSE profile {g['groupReference']}: {bad}")
        (crtdl_dir / f"{name}.json").write_text(json.dumps(crtdl, indent=2, ensure_ascii=False))
        coverage.append({"crtdl": name, "url": url, "variants": nvar, "fields": len(fids),
                         "uncovered_fields": [f for f in fids if f not in covered],
                         "references": len(refs),
                         "uncovered_references": [r for r in refs if r in targets and r not in covered],
                         "unlinked_references": [r for r in refs if r not in targets]})

    resources += gen.stubs.values()
    bundle = {"resourceType": "Bundle", "type": "transaction",
              "entry": [{"resource": r, "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}}
                        for r in resources]}
    data_dir = args.out_dir / "testdata"
    data_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = data_dir / "ontology-testdata.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False))
    print(f"{len(entries)} CRTDLs in {crtdl_dir}")
    print(f"{len(resources)} resources ({len(gen.stubs)} stubs) in {bundle_path}")
    write_coverage(args.out_dir, coverage, gen.issues)
    if args.upload:
        upload(bundle_path, args.fhir_url)


if __name__ == "__main__":
    main()
