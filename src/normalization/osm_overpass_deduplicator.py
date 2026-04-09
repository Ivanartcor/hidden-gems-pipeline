from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

from src.normalization.place_candidate import NormalizedPlaceCandidate


@dataclass(slots=True)
class DuplicatePairEvidence:
    left_candidate_key: str
    right_candidate_key: str
    score: float
    distance_m: float | None
    signals: list[str] = field(default_factory=list)
    hard_rule_triggered: str | None = None


@dataclass(slots=True)
class DuplicateGroup:
    group_id: str
    representative_key: str
    representative_candidate: NormalizedPlaceCandidate
    member_keys: list[str]
    member_candidates: list[NormalizedPlaceCandidate]
    evidences: list[DuplicatePairEvidence] = field(default_factory=list)


@dataclass(slots=True)
class DeduplicationResult:
    input_count: int
    processed_count: int
    grouped_duplicate_count: int
    output_count: int
    unique_candidates: list[NormalizedPlaceCandidate]
    duplicate_groups: list[DuplicateGroup]
    pair_evidences: list[DuplicatePairEvidence]


class OSMOverpassDeduplicator:
    """
    Deduplicación intra-fuente para candidatos de Overpass.
    No modifica la base de datos ni consolida todavía en `place`.
    Solo agrupa candidatos que parecen representar el mismo local
    dentro de la propia fuente OSM.
    """

    def __init__(
        self,
        *,
        max_name_distance_m: float = 20.0,
        max_contact_distance_m: float = 60.0,
        score_threshold: float = 0.75,
    ) -> None:
        self.max_name_distance_m = max_name_distance_m
        self.max_contact_distance_m = max_contact_distance_m
        self.score_threshold = score_threshold

    @staticmethod
    def _candidate_key(candidate: NormalizedPlaceCandidate) -> str:
        return (
            f"{candidate.provenance.source_system_code}:"
            f"{candidate.provenance.source_entity_type}:"
            f"{candidate.provenance.source_record_id}"
        )

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None

        digits = re.sub(r"[^\d+]", "", value.strip())
        return digits or None

    @staticmethod
    def _normalize_website(value: str | None) -> str | None:
        if not value:
            return None

        website = value.strip().lower()
        website = re.sub(r"^https?://", "", website)
        website = website.rstrip("/")
        return website or None

    @staticmethod
    def _normalize_name(value: str | None) -> str | None:
        if not value:
            return None
        return value.strip().lower() or None

    @staticmethod
    def _normalize_address(value: str | None) -> str | None:
        if not value:
            return None
        return re.sub(r"\s+", " ", value.strip().lower()) or None

    @staticmethod
    def _same_text(left: str | None, right: str | None) -> bool:
        return bool(left and right and left == right)

    @staticmethod
    def _haversine_distance_m(
        lat1: float | None,
        lon1: float | None,
        lat2: float | None,
        lon2: float | None,
    ) -> float | None:
        if None in {lat1, lon1, lat2, lon2}:
            return None

        radius_m = 6_371_000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius_m * c

    def _representative_rank(
        self,
        candidate: NormalizedPlaceCandidate,
    ) -> tuple:
        quality = candidate.quality
        business = candidate.business
        address = candidate.address

        return (
            quality.completeness_score or 0.0,
            1 if quality.has_address else 0,
            1 if quality.has_contact_info else 0,
            1 if quality.has_opening_hours else 0,
            1 if business.website_url else 0,
            1 if business.phone_normalized or business.phone_raw else 0,
            1 if address.source_address_raw else 0,
            len(candidate.names.display_name or ""),
        )

    def _compare_pair(
        self,
        left: NormalizedPlaceCandidate,
        right: NormalizedPlaceCandidate,
    ) -> DuplicatePairEvidence | None:
        left_name = self._normalize_name(left.names.normalized_name)
        right_name = self._normalize_name(right.names.normalized_name)

        left_phone = self._normalize_phone(
            left.business.phone_normalized or left.business.phone_raw
        )
        right_phone = self._normalize_phone(
            right.business.phone_normalized or right.business.phone_raw
        )

        left_website = self._normalize_website(left.business.website_url)
        right_website = self._normalize_website(right.business.website_url)

        left_brand = self._normalize_name(left.names.brand_raw)
        right_brand = self._normalize_name(right.names.brand_raw)

        left_category = self._normalize_name(
            left.classification.source_primary_category_raw
        )
        right_category = self._normalize_name(
            right.classification.source_primary_category_raw
        )

        left_address = self._normalize_address(left.address.source_address_normalized)
        right_address = self._normalize_address(right.address.source_address_normalized)

        distance_m = self._haversine_distance_m(
            left.location.latitude,
            left.location.longitude,
            right.location.latitude,
            right.location.longitude,
        )

        same_name = self._same_text(left_name, right_name)
        same_phone = self._same_text(left_phone, right_phone)
        same_website = self._same_text(left_website, right_website)
        same_brand = self._same_text(left_brand, right_brand)
        same_category = self._same_text(left_category, right_category)
        same_address = self._same_text(left_address, right_address)

        nearby_name = distance_m is not None and distance_m <= self.max_name_distance_m
        nearby_contact = distance_m is not None and distance_m <= self.max_contact_distance_m

        signals: list[str] = []
        score = 0.0
        hard_rule_triggered: str | None = None

        # La dirección exacta es una señal muy fuerte cuando existe
        if same_address:
            score += 0.45
            signals.append("same_normalized_address")

        # El nombre ayuda, pero ya no basta por sí solo
        if same_name:
            score += 0.20
            signals.append("same_normalized_name")

        # Señales de proximidad
        if distance_m is not None:
            if distance_m <= 5:
                score += 0.45
                signals.append("distance_le_5m")
            elif distance_m <= 15:
                score += 0.30
                signals.append("distance_le_15m")
            elif distance_m <= 30:
                score += 0.20
                signals.append("distance_le_30m")

        # Categoría solo suma si ya hay cercanía geográfica
        if same_category and nearby_name:
            score += 0.10
            signals.append("same_primary_category_nearby")

        # Marca solo suma si además están cerca o comparten dirección
        if same_brand and left_brand is not None and (nearby_name or same_address):
            score += 0.10
            signals.append("same_brand_with_local_support")

        # Teléfono y web solo suman fuerte si hay soporte local
        if same_phone and (nearby_contact or same_address):
            score += 0.45
            signals.append("same_phone_with_local_support")

        if same_website and (nearby_contact or same_address):
            score += 0.45
            signals.append("same_website_with_local_support")

        # Reglas duras: solo con soporte espacial o de dirección
        if same_name and same_address:
            hard_rule_triggered = "same_name_and_same_address"

        if same_name and nearby_name:
            hard_rule_triggered = "same_name_and_nearby"

        if same_phone and (nearby_contact or same_address):
            hard_rule_triggered = "same_phone_with_local_support"

        if same_website and (nearby_contact or same_address):
            hard_rule_triggered = "same_website_with_local_support"

        if not signals:
            return None

        is_duplicate = bool(hard_rule_triggered) or score >= self.score_threshold
        if not is_duplicate:
            return None

        return DuplicatePairEvidence(
            left_candidate_key=self._candidate_key(left),
            right_candidate_key=self._candidate_key(right),
            score=round(min(score, 1.0), 4),
            distance_m=round(distance_m, 2) if distance_m is not None else None,
            signals=signals,
            hard_rule_triggered=hard_rule_triggered,
        )

    def deduplicate_candidates(
        self,
        candidates: list[NormalizedPlaceCandidate],
        *,
        include_statuses: tuple[str, ...] = ("accepted",),
    ) -> DeduplicationResult:
        filtered_candidates = [
            candidate
            for candidate in candidates
            if candidate.quality.candidate_status in include_statuses
        ]

        candidate_by_key = {
            self._candidate_key(candidate): candidate
            for candidate in filtered_candidates
        }

        keys = list(candidate_by_key.keys())

        # Índices de bloqueo para no comparar todo con todo.
        by_name: defaultdict[str, list[str]] = defaultdict(list)
        by_phone: defaultdict[str, list[str]] = defaultdict(list)
        by_website: defaultdict[str, list[str]] = defaultdict(list)

        for key, candidate in candidate_by_key.items():
            normalized_name = self._normalize_name(candidate.names.normalized_name)
            phone = self._normalize_phone(
                candidate.business.phone_normalized or candidate.business.phone_raw
            )
            website = self._normalize_website(candidate.business.website_url)

            if normalized_name:
                by_name[normalized_name].append(key)

            if phone:
                by_phone[phone].append(key)

            if website:
                by_website[website].append(key)

        candidate_pairs: set[tuple[str, str]] = set()

        def add_pairs_from_index(index_map: dict[str, list[str]]) -> None:
            for key_list in index_map.values():
                if len(key_list) < 2:
                    continue

                for i in range(len(key_list)):
                    for j in range(i + 1, len(key_list)):
                        left_key, right_key = sorted((key_list[i], key_list[j]))
                        candidate_pairs.add((left_key, right_key))

        add_pairs_from_index(by_name)
        add_pairs_from_index(by_phone)
        add_pairs_from_index(by_website)

        pair_evidences: list[DuplicatePairEvidence] = []
        parent = {key: key for key in keys}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_y] = root_x

        for left_key, right_key in sorted(candidate_pairs):
            left_candidate = candidate_by_key[left_key]
            right_candidate = candidate_by_key[right_key]

            evidence = self._compare_pair(left_candidate, right_candidate)
            if evidence is None:
                continue

            pair_evidences.append(evidence)
            union(left_key, right_key)

        groups_map: defaultdict[str, list[str]] = defaultdict(list)
        for key in keys:
            root = find(key)
            groups_map[root].append(key)

        duplicate_groups: list[DuplicateGroup] = []
        unique_candidates: list[NormalizedPlaceCandidate] = []
        grouped_duplicate_count = 0

        evidence_map: defaultdict[frozenset[str], list[DuplicatePairEvidence]] = defaultdict(list)
        for evidence in pair_evidences:
            pair_key = frozenset(
                [evidence.left_candidate_key, evidence.right_candidate_key]
            )
            evidence_map[pair_key].append(evidence)

        group_counter = 1

        for group_keys in groups_map.values():
            group_candidates = [candidate_by_key[key] for key in group_keys]

            if len(group_keys) == 1:
                unique_candidates.append(group_candidates[0])
                continue

            grouped_duplicate_count += len(group_keys) - 1

            representative_candidate = max(
                group_candidates,
                key=self._representative_rank,
            )
            representative_key = self._candidate_key(representative_candidate)

            group_evidences: list[DuplicatePairEvidence] = []
            for i in range(len(group_keys)):
                for j in range(i + 1, len(group_keys)):
                    pair_key = frozenset([group_keys[i], group_keys[j]])
                    group_evidences.extend(evidence_map.get(pair_key, []))

            duplicate_groups.append(
                DuplicateGroup(
                    group_id=f"osm_overpass_group_{group_counter:05d}",
                    representative_key=representative_key,
                    representative_candidate=representative_candidate,
                    member_keys=sorted(group_keys),
                    member_candidates=group_candidates,
                    evidences=group_evidences,
                )
            )
            unique_candidates.append(representative_candidate)
            group_counter += 1

        return DeduplicationResult(
            input_count=len(candidates),
            processed_count=len(filtered_candidates),
            grouped_duplicate_count=grouped_duplicate_count,
            output_count=len(unique_candidates),
            unique_candidates=unique_candidates,
            duplicate_groups=duplicate_groups,
            pair_evidences=pair_evidences,
        )