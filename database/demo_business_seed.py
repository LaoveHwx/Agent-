from typing import Any

from tools.postgres_tool import get_connection


PRODUCTS = [
    (1, "智能巡检套件", "SaaS", 12800.00, "active"),
    (2, "数据治理服务", "Service", 22000.00, "active"),
    (3, "知识库问答助手", "AI", 16800.00, "active"),
    (4, "销售预测模块", "AI", 18800.00, "active"),
    (5, "运维监控插件", "SaaS", 9800.00, "active"),
]

SALES_ORDERS = [
    (1001, "2026-03-05", "华东", "直销", "大型企业", 1, 6, 76800.00, 0.10),
    (1002, "2026-03-11", "华东", "伙伴", "中型企业", 2, 3, 66000.00, 0.06),
    (1003, "2026-03-21", "华南", "直销", "大型企业", 3, 5, 84000.00, 0.08),
    (1004, "2026-03-28", "华北", "线上", "中型企业", 5, 4, 39200.00, 0.02),
    (1005, "2026-04-04", "华东", "直销", "大型企业", 2, 5, 110000.00, 0.07),
    (1006, "2026-04-13", "华东", "伙伴", "中型企业", 4, 4, 75200.00, 0.09),
    (1007, "2026-04-18", "西南", "直销", "大型企业", 1, 3, 38400.00, 0.05),
    (1008, "2026-04-24", "华南", "线上", "小微企业", 3, 2, 33600.00, 0.03),
    (1009, "2026-05-06", "华东", "伙伴", "中型企业", 2, 2, 44000.00, 0.12),
    (1010, "2026-05-16", "华东", "线上", "小微企业", 5, 3, 29400.00, 0.05),
    (1011, "2026-05-18", "华北", "直销", "大型企业", 2, 4, 88000.00, 0.04),
    (1012, "2026-05-29", "华南", "伙伴", "中型企业", 4, 3, 56400.00, 0.08),
    (1013, "2026-06-03", "华东", "线上", "小微企业", 1, 2, 25600.00, 0.06),
    (1014, "2026-06-10", "华东", "伙伴", "中型企业", 3, 1, 16800.00, 0.14),
    (1015, "2026-06-20", "华南", "直销", "大型企业", 2, 6, 132000.00, 0.05),
    (1016, "2026-06-26", "华北", "伙伴", "中型企业", 4, 2, 37600.00, 0.06),
    (1017, "2026-07-03", "华东", "直销", "大型企业", 2, 4, 88000.00, 0.06),
    (1018, "2026-07-09", "华东", "伙伴", "中型企业", 4, 2, 37600.00, 0.08),
    (1019, "2026-07-16", "华南", "线上", "小微企业", 5, 6, 58800.00, 0.04),
    (1020, "2026-07-22", "西南", "直销", "大型企业", 3, 4, 67200.00, 0.07),
]

REGION_EVENTS = [
    (1, "2026-05-01", "华东", "渠道", "华东伙伴渠道折扣收紧，部分中型客户订单延后。", "medium"),
    (2, "2026-06-01", "华东", "供给", "知识库问答助手华东交付排期延长，影响六月确认收入。", "high"),
    (3, "2026-07-01", "华东", "恢复", "直销团队补充重点客户跟进，华东七月销售恢复。", "medium"),
    (4, "2026-06-15", "华南", "大单", "华南大型企业客户集中采购数据治理服务。", "medium"),
]


def seed_demo_business_data() -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS biz_products (
                    product_id INTEGER PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    list_price NUMERIC(12, 2) NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS biz_sales_orders (
                    order_id INTEGER PRIMARY KEY,
                    order_date DATE NOT NULL,
                    region TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    customer_segment TEXT NOT NULL,
                    product_id INTEGER NOT NULL REFERENCES biz_products(product_id),
                    quantity INTEGER NOT NULL,
                    revenue NUMERIC(12, 2) NOT NULL,
                    discount_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS biz_region_events (
                    event_id INTEGER PRIMARY KEY,
                    event_date DATE NOT NULL,
                    region TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    impact_level TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cur.executemany(
                """
                INSERT INTO biz_products (product_id, product_name, category, list_price, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (product_id) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    category = EXCLUDED.category,
                    list_price = EXCLUDED.list_price,
                    status = EXCLUDED.status,
                    updated_at = now()
                """,
                PRODUCTS,
            )
            cur.executemany(
                """
                INSERT INTO biz_sales_orders (
                    order_id,
                    order_date,
                    region,
                    channel,
                    customer_segment,
                    product_id,
                    quantity,
                    revenue,
                    discount_rate
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET
                    order_date = EXCLUDED.order_date,
                    region = EXCLUDED.region,
                    channel = EXCLUDED.channel,
                    customer_segment = EXCLUDED.customer_segment,
                    product_id = EXCLUDED.product_id,
                    quantity = EXCLUDED.quantity,
                    revenue = EXCLUDED.revenue,
                    discount_rate = EXCLUDED.discount_rate,
                    updated_at = now()
                """,
                SALES_ORDERS,
            )
            cur.executemany(
                """
                INSERT INTO biz_region_events (
                    event_id,
                    event_date,
                    region,
                    event_type,
                    description,
                    impact_level
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE SET
                    event_date = EXCLUDED.event_date,
                    region = EXCLUDED.region,
                    event_type = EXCLUDED.event_type,
                    description = EXCLUDED.description,
                    impact_level = EXCLUDED.impact_level,
                    updated_at = now()
                """,
                REGION_EVENTS,
            )
            conn.commit()

    return {
        "status": "ok",
        "tables": ["public.biz_products", "public.biz_sales_orders", "public.biz_region_events"],
        "rows": {
            "biz_products": len(PRODUCTS),
            "biz_sales_orders": len(SALES_ORDERS),
            "biz_region_events": len(REGION_EVENTS),
        },
    }
