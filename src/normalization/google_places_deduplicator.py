from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from src.normalization.place_candidate import NormalizedPlaceCandidate


@dataclass(slots=True)
class GooglePlacesDuplicatePairEvidence:
    left_candidate_key: str
    right_candidate_key: str
    score: float
    distance_m: float | None
    signals: list[str] = field(default_factory=list)
    hard_rule_triggered: str | None = None


@dataclass(slots=True)
class GooglePlacesDuplicateGroup:
    group_id: str
    representative_key: str
    representative_candidate: NormalizedPlaceCandidate
    member_keys: list[str]
    member_candidates: list[NormalizedPlaceCandidate]
    evidences: list[GooglePlacesDuplicatePairEvidence] = field(default_factory=list)


@dataclass(slots=True)
class GooglePlacesDeduplicationResult:
    input_count: int
    processed_count: int
    grouped_duplicate_count: int
    output_count: int
    unique_candidates: list[NormalizedPlaceCandidate]
    duplicate_groups: list[GooglePlacesDuplicateGroup]
    pair_evidences: list[GooglePlacesDuplicatePairEvidence]


class GooglePlacesDeduplicator:
    """
    Deduplicación intra-fuente para candidatos de Google Places.

    No escribe en base de datos ni consolida todavía en `place`.
    Solo agrupa candidatos repetidos dentro del staging de Google Places.

    Prioridad de deduplicación:
    1. Mismo Google Place ID.
    2. Mismo nombre normalizado y coordenadas prácticamente iguales.
    3. Mismo nombre normalizado y distancia muy pequeña.
    """

    def __init__(
        self,
        *,
        max_same_name_distance_m: float = 15.0,
        score_threshold: float = 0.85,
    ) -> None:
        self.max_same_name_distance_m = max_same_name_distance_m
        self.score_threshold = score_threshold

    @staticmethod
    def _candidate_key(candidate: NormalizedPlaceCandidate) -> str:
        return (
            f"{candidate.provenance.source_system_code}:"
            f"{candidate.provenance.source_entity_type}:"
            f"{candidate.provenance.source_record_id}"
        )

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if not value:
            return None

        return value.strip().lower() or None

    @staticmethod
    def _rounded_coord_key(
        latitude: float | None,
        longitude: float | None,
        *,
        decimals: int = 5,
    ) -> str | None:
        if latitude is None or longitude is None:
            return None

        return f"{round(latitude, decimals)},{round(longitude, decimals)}"

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
        provenance = candidate.provenance

        return (
            quality.completeness_score or 0.0,
            1 if quality.has_address else 0,
            1 if quality.has_contact_info else 0,
            1 if provenance.source_status_raw == "OPERATIONAL" else 0,
            1 if provenance.source_url else 0,
            1 if business.website_url else 0,
            1 if business.phone_normalized or business.phone_raw else 0,
            1 if address.source_address_raw else 0,
            len(candidate.names.display_name or ""),
        )

    def _compare_pair(
        self,
        left: NormalizedPlaceCandidate,
        right: NormalizedPlaceCandidate,
    ) -> GooglePlacesDuplicatePairEvidence | None:
        left_key = self._candidate_key(left)
        right_key = self._candidate_key(right)

        left_place_id = self._normalize_text(left.provenance.source_record_id)
        right_place_id = self._normalize_text(right.provenance.source_record_id)

        left_name = self._normalize_text(left.names.normalized_name)
        right_name = self._normalize_text(right.names.normalized_name)

        left_coord_key = self._rounded_coord_key(
            left.location.latitude,
            left.location.longitude,
        )
        right_coord_key = self._rounded_coord_key(
            right.location.latitude,
            right.location.longitude,
        )

        distance_m = self._haversine_distance_m(
            left.location.latitude,
            left.location.longitude,
            right.location.latitude,
            right.location.longitude,
        )

        same_source_record_id = bool(
            left_place_id
            and right_place_id
            and left_place_id == right_place_id
        )
        same_name = bool(left_name and right_name and left_name == right_name)
        same_rounded_coordinates = bool(
            left_coord_key
            and right_coord_key
            and left_coord_key == right_coord_key
        )
        very_near = (
            distance_m is not None
            and distance_m <= self.max_same_name_distance_m
        )

        score = 0.0
        signals: list[str] = []
        hard_rule_triggered: str | None = None

        if same_source_record_id:
            score = 1.0
            signals.append("same_google_place_id")
            hard_rule_triggered = "same_google_place_id"

        if same_name:
            score += 0.35
            signals.append("same_normalized_name")

        if same_rounded_coordinates:
            score += 0.45
            signals.append("same_rounded_coordinates")

        if very_near:
            score += 0.35
            signals.append("distance_le_threshold")

        if same_name and same_rounded_coordinates:
            hard_rule_triggered = "same_name_and_same_rounded_coordinates"

        if same_name and very_near:
            hard_rule_triggered = "same_name_and_very_near"

        if not signals:
            return None

        score = round(min(score, 1.0), 4)

        is_duplicate = bool(hard_rule_triggered) or score >= self.score_threshold
        if not is_duplicate:
            return None

        return GooglePlacesDuplicatePairEvidence(
            left_candidate_key=left_key,
            right_candidate_key=right_key,
            score=score,
            distance_m=round(distance_m, 2) if distance_m is not None else None,
            signals=signals,
            hard_rule_triggered=hard_rule_triggered,
        )

    def deduplicate_candidates(
        self,
        candidates: list[NormalizedPlaceCandidate],
        *,
        include_statuses: tuple[str, ...] = ("accepted",),
    ) -> GooglePlacesDeduplicationResult:
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

        by_source_record_id: defaultdict[str, list[str]] = defaultdict(list)
        by_name: defaultdict[str, list[str]] = defaultdict(list)
        by_name_and_coord: defaultdict[str, list[str]] = defaultdict(list)

        for key, candidate in candidate_by_key.items():
            source_record_id = self._normalize_text(candidate.provenance.source_record_id)
            normalized_name = self._normalize_text(candidate.names.normalized_name)
            coord_key = self._rounded_coord_key(
                candidate.location.latitude,
                candidate.location.longitude,
            )

            if source_record_id:
                by_source_record_id[source_record_id].append(key)

            if normalized_name:
                by_name[normalized_name].append(key)

            if normalized_name and coord_key:
                by_name_and_coord[f"{normalized_name}|{coord_key}"].append(key)

        candidate_pairs: set[tuple[str, str]] = set()

        def add_pairs_from_index(index_map: dict[str, list[str]]) -> None:
            for key_list in index_map.values():
                if len(key_list) < 2:
                    continue

                for i in range(len(key_list)):
                    for j in range(i + 1, len(key_list)):
                        left_key, right_key = sorted((key_list[i], key_list[j]))
                        candidate_pairs.add((left_key, right_key))

        add_pairs_from_index(by_source_record_id)
        add_pairs_from_index(by_name)
        add_pairs_from_index(by_name_and_coord)

        parent = {key: key for key in keys}
        pair_evidences: list[GooglePlacesDuplicatePairEvidence] = []

        def find(value: str) -> str:
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(left_value: str, right_value: str) -> None:
            left_root = find(left_value)
            right_root = find(right_value)

            if left_root != right_root:
                parent[right_root] = left_root

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
            groups_map[find(key)].append(key)

        duplicate_groups: list[GooglePlacesDuplicateGroup] = []
        unique_candidates: list[NormalizedPlaceCandidate] = []
        grouped_duplicate_count = 0
        group_counter = 1

        evidence_map: defaultdict[frozenset[str], list[GooglePlacesDuplicatePairEvidence]] = defaultdict(list)

        for evidence in pair_evidences:
            pair_key = frozenset(
                [
                    evidence.left_candidate_key,
                    evidence.right_candidate_key,
                ]
            )
            evidence_map[pair_key].append(evidence)

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

            group_evidences: list[GooglePlacesDuplicatePairEvidence] = []

            for i in range(len(group_keys)):
                for j in range(i + 1, len(group_keys)):
                    pair_key = frozenset([group_keys[i], group_keys[j]])
                    group_evidences.extend(evidence_map.get(pair_key, []))

            duplicate_groups.append(
                GooglePlacesDuplicateGroup(
                    group_id=f"google_places_group_{group_counter:05d}",
                    representative_key=representative_key,
                    representative_candidate=representative_candidate,
                    member_keys=sorted(group_keys),
                    member_candidates=group_candidates,
                    evidences=group_evidences,
                )
            )

            unique_candidates.append(representative_candidate)
            group_counter += 1

        return GooglePlacesDeduplicationResult(
            input_count=len(candidates),
            processed_count=len(filtered_candidates),
            grouped_duplicate_count=grouped_duplicate_count,
            output_count=len(unique_candidates),
            unique_candidates=unique_candidates,
            duplicate_groups=duplicate_groups,
            pair_evidences=pair_evidences,
        )