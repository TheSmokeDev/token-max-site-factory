"""Writer packet builder — port of sr22_token_max.py page_prompt_packet()
L283-348. The packet is the writer's ONLY page-specific fact source."""

from __future__ import annotations

from .config import topic_packet_config, topics_by_key


def _format_vars(cfg: dict, entity: dict, topic: dict) -> dict:
    vars: dict[str, object] = {
        "domain": cfg.get("domain"),
        "canonical_host": cfg.get("canonical_host"),
        "topic_key": topic.get("key"),
        "topic_label": topic.get("label"),
        "topic_title_label": topic.get("title_label"),
    }
    for key, value in entity.items():
        if isinstance(value, (str, int, float)) or value is None:
            vars[f"entity_{key}"] = value
    return vars


def page_prompt_packet(cfg: dict, page: dict, batch: dict, entities: dict[str, dict]) -> dict:
    topic_key = str(page["product"])
    topic = topics_by_key(cfg)[topic_key]
    entity = entities[str(page["city"])]
    fm_cfg = cfg.get("frontmatter") or {}
    quality = cfg["quality"]
    vars = _format_vars(cfg, entity, topic)

    packet = {
        "complete": False,
        "batch_kind": batch.get("kind"),
        "page_id": page["id"],
        "status": page.get("status"),
        "retry_count": int(page.get("retry_count") or 0),
        "validation_failures": page.get("validation_failures", []),
        "regenerate_with": page.get("regenerate_with", ""),
        "output": page["output"],
        "route": page["route"],
        "city": entity,
        "product": topic_key,
        "product_config": topic_packet_config(topic),
        "authority_sources": cfg.get("authority_sources") or [],
        "comparison_corpus": cfg.get("comparison_corpus") or {},
        "frontmatter": {
            "title": str(fm_cfg.get("title_template") or "").format(**vars),
            "description": str(fm_cfg.get("description_template") or "").format(**vars),
            "city": entity.get("slug"),
            "product": topic_key,
            "locale": "en",
            "published": batch.get("published") or fm_cfg.get("published") or "",
            "updated": batch.get("updated") or fm_cfg.get("updated") or "",
        },
        "writer_contract": {
            "target_words": f"{quality['target_words_min']}-{quality['target_words_max']}",
            "hard_min_words": quality["hard_min_words"],
            "min_h2_sections": quality["min_h2"],
            "min_faq_questions": quality["min_faq_questions"],
            "min_ai_citable_passages": quality["min_ai_citable_passages"],
            "text_to_html_ratio_min": quality["min_text_html_ratio"],
            "max_pairwise_overlap": quality["max_pairwise_overlap"],
            "must_include": list((cfg.get("writer_contract") or {}).get("must_include") or []),
            "must_not_include": list((cfg.get("writer_contract") or {}).get("must_not_include") or []),
        },
    }
    if page.get("staging"):
        packet["staging"] = page["staging"]
        packet["page_format"] = cfg.get("page_format")
    return packet
