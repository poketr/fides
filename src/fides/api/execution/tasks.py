from fides.api.graph.traversal import Traversal
from typing import Set, Dict

from fides.api.db.ctl_session import sync_session
from fides.api.models.privacy_request import PrivacyRequest
from fides.api import common_exceptions


from fides.api.graph.graph import DatasetGraph
from fides.api.models.datasetconfig import DatasetConfig

test_traversal_map = (
    {
        "__ROOT__:__ROOT__": {
            "from": {},
            "to": {
                "mongo_test:internal_customer_profile": {
                    "email -> customer_identifiers.derived_emails"
                },
                "postgres_example_test_dataset:employee": {"email -> email"},
                "postgres_example_test_dataset:service_request": {
                    "email -> alt_email",
                    "email -> email",
                },
                "postgres_example_test_dataset:visit": {"email -> email"},
                "mongo_test:customer_feedback": {"email -> customer_information.email"},
                "postgres_example_test_dataset:customer": {"email -> email"},
                "mongo_test:employee": {"email -> email"},
                "postgres_example_test_dataset:report": {"email -> email"},
            },
        },
        "mongo_test:internal_customer_profile": {
            "from": {
                "__ROOT__:__ROOT__": {"email -> customer_identifiers.derived_emails"},
                "mongo_test:customer_feedback": {
                    "customer_information.internal_customer_id -> customer_identifiers.internal_id"
                },
            },
            "to": {
                "mongo_test:rewards": {
                    "customer_identifiers.derived_phone -> owner.phone"
                }
            },
        },
        "postgres_example_test_dataset:employee": {
            "from": {"__ROOT__:__ROOT__": {"email -> email"}},
            "to": {
                "postgres_example_test_dataset:service_request": {"id -> employee_id"},
                "postgres_example_test_dataset:address": {"address_id -> id"},
            },
        },
        "postgres_example_test_dataset:service_request": {
            "from": {
                "postgres_example_test_dataset:employee": {"id -> employee_id"},
                "__ROOT__:__ROOT__": {"email -> alt_email", "email -> email"},
            },
            "to": {},
        },
        "postgres_example_test_dataset:visit": {
            "from": {"__ROOT__:__ROOT__": {"email -> email"}},
            "to": {},
        },
        "mongo_test:customer_feedback": {
            "from": {"__ROOT__:__ROOT__": {"email -> customer_information.email"}},
            "to": {
                "mongo_test:internal_customer_profile": {
                    "customer_information.internal_customer_id -> customer_identifiers.internal_id"
                }
            },
        },
        "postgres_example_test_dataset:customer": {
            "from": {"__ROOT__:__ROOT__": {"email -> email"}},
            "to": {
                "postgres_example_test_dataset:address": {"address_id -> id"},
                "postgres_example_test_dataset:orders": {"id -> customer_id"},
                "postgres_example_test_dataset:login": {"id -> customer_id"},
                "postgres_example_test_dataset:payment_card": {"id -> customer_id"},
                "mongo_test:customer_details": {"id -> customer_id"},
            },
        },
        "mongo_test:employee": {
            "from": {
                "mongo_test:flights": {"pilots -> id"},
                "__ROOT__:__ROOT__": {"email -> email"},
            },
            "to": {},
        },
        "postgres_example_test_dataset:report": {
            "from": {"__ROOT__:__ROOT__": {"email -> email"}},
            "to": {},
        },
        "mongo_test:rewards": {
            "from": {
                "mongo_test:internal_customer_profile": {
                    "customer_identifiers.derived_phone -> owner.phone"
                }
            },
            "to": {},
        },
        "postgres_example_test_dataset:address": {
            "from": {
                "postgres_example_test_dataset:orders": {"shipping_address_id -> id"},
                "postgres_example_test_dataset:customer": {"address_id -> id"},
                "postgres_example_test_dataset:employee": {"address_id -> id"},
                "postgres_example_test_dataset:payment_card": {
                    "billing_address_id -> id"
                },
            },
            "to": {},
        },
        "postgres_example_test_dataset:orders": {
            "from": {"postgres_example_test_dataset:customer": {"id -> customer_id"}},
            "to": {
                "postgres_example_test_dataset:address": {"shipping_address_id -> id"},
                "postgres_example_test_dataset:order_item": {"id -> order_id"},
            },
        },
        "postgres_example_test_dataset:login": {
            "from": {"postgres_example_test_dataset:customer": {"id -> customer_id"}},
            "to": {},
        },
        "postgres_example_test_dataset:payment_card": {
            "from": {"postgres_example_test_dataset:customer": {"id -> customer_id"}},
            "to": {
                "postgres_example_test_dataset:address": {"billing_address_id -> id"}
            },
        },
        "mongo_test:customer_details": {
            "from": {"postgres_example_test_dataset:customer": {"id -> customer_id"}},
            "to": {
                "mongo_test:conversations": {"comments.comment_id -> thread.comment"},
                "mongo_test:flights": {
                    "travel_identifiers -> passenger_information.passenger_ids"
                },
            },
        },
        "postgres_example_test_dataset:order_item": {
            "from": {"postgres_example_test_dataset:orders": {"id -> order_id"}},
            "to": {"postgres_example_test_dataset:product": {"product_id -> id"}},
        },
        "mongo_test:conversations": {
            "from": {
                "mongo_test:customer_details": {"comments.comment_id -> thread.comment"}
            },
            "to": {"mongo_test:payment_card": {"thread.ccn -> ccn"}},
        },
        "mongo_test:flights": {
            "from": {
                "mongo_test:customer_details": {
                    "travel_identifiers -> passenger_information.passenger_ids"
                }
            },
            "to": {
                "mongo_test:employee": {"pilots -> id"},
                "mongo_test:aircraft": {"plane -> planes"},
            },
        },
        "postgres_example_test_dataset:product": {
            "from": {"postgres_example_test_dataset:order_item": {"product_id -> id"}},
            "to": {},
        },
        "mongo_test:payment_card": {
            "from": {"mongo_test:conversations": {"thread.ccn -> ccn"}},
            "to": {},
        },
        "mongo_test:aircraft": {
            "from": {"mongo_test:flights": {"plane -> planes"}},
            "to": {},
        },
    },
    [
        "mongo_test:internal_customer_profile",
        "postgres_example_test_dataset:service_request",
        "postgres_example_test_dataset:visit",
        "mongo_test:employee",
        "postgres_example_test_dataset:report",
        "mongo_test:rewards",
        "postgres_example_test_dataset:address",
        "postgres_example_test_dataset:login",
        "postgres_example_test_dataset:product",
        "mongo_test:payment_card",
        "mongo_test:aircraft",
    ],
)


def load_graph_into_db(privacy_request_id: str) -> Traversal:
    """
    Load the traversal graph into the database.
    """
    with sync_session() as session:
        # Get the privacy request from the database
        privacy_request = PrivacyRequest.get(db=session, object_id=privacy_request_id)
        if not privacy_request:
            raise common_exceptions.PrivacyRequestNotFound(
                f"Privacy request with id {privacy_request_id} not found"
            )

        graph = DatasetGraph(
            *[
                dataset_config.get_graph()
                for dataset_config in DatasetConfig.all(db=session)
            ]
        )
        identity = privacy_request.get_cached_identity_data()
        traversal: Traversal = Traversal(graph, identity)
        return traversal

        # Convert the traversal graph into discrete tasks that have full "downstream" and "upstream" values

        # Load the traversal into the database


def format_traversal_map(
    traversal_map: Dict[str, Dict[str, Dict[str, Set]]]
) -> Dict[str, Dict[str, Set]]:
    """
    Returns a reformatted traversal graph with the following format:

    {"postgres_db:order_item.order_id":
        {"upstream": {"postgres_other:address.customer_id"}},
        {"downstream": {"postgres_other:some_table"}},}

    Glossary:
        - Upstream = A value that relied on the current value. It has already
          been accessed/erased by the time we are at the current node.
        - Downstream = Refers to the _next_ value that will be accessed/erased
          after the current value.

    Remember, we want to work "backwards" and start with accessing/deleting
    values as far from the original primary key as possible.

    """
    references: Dict[str, Dict[str, Set]] = {}

    for dataset, relations in traversal_map.items():
        # Loop through the "from" items, which we rename to "downstream"
        for relational_dataset, relation in relations["from"].items():
            foreign_field, local_field = list(relation)[0].split(" -> ")
            foreign_reference = f"{relational_dataset}.{foreign_field}"
            current_reference = f"{dataset}.{local_field}"

            references[current_reference] = references.get(current_reference, {})
            references[current_reference]["downstream"] = (
                references[current_reference]
                .get("downstream", set)
                .union({foreign_reference})
            )

            references[foreign_reference] = references.get(foreign_reference, {})
            references[foreign_reference]["upstream"] = (
                references[foreign_reference]
                .get("upstream", set)
                .union({current_reference})
            )

        # Loop through the "to" items, which we rename to "upstream"
        for relational_dataset, relation in relations["to"].items():
            local_field, foreign_field = list(relation)[0].split(" -> ")
            foreign_reference = f"{relational_dataset}.{foreign_field}"
            current_reference = f"{dataset}.{local_field}"

            references[current_reference] = references.get(current_reference, {})
            references[current_reference]["upstream"] = (
                references[current_reference]
                .get("upstream", set)
                .union({foreign_reference})
            )

            references[foreign_reference] = references.get(foreign_reference, {})
            references[foreign_reference]["downstream"] = (
                references[foreign_reference]
                .get("downstream", set)
                .union({current_reference})
            )

    sorted_references = {key: references[key] for key in sorted(references.keys())}
    return sorted_references


test_traversal_map_1 = {
    "postgres_example_test_dataset:employee": {
        "from": {"__ROOT__:__ROOT__": {"email -> email"}},
        "to": {
            "postgres_example_test_dataset:service_request": {"id -> employee_id"},
            "postgres_example_test_dataset:address": {"address_id -> id"},
        },
    },
    "postgres_example_test_dataset:service_request": {
        "from": {
            "postgres_example_test_dataset:employee": {"id -> employee_id"},
            "__ROOT__:__ROOT__": {"email -> alt_email", "email -> email"},
        },
        "to": {},
    },
    "postgres_example_test_dataset:visit": {
        "from": {"__ROOT__:__ROOT__": {"email -> email"}},
        "to": {"postgres_example_test_dataset:employee": {"email -> employee_id"}},
    },
}


def test_flatten_stuff():
    references = format_traversal_map(test_traversal_map_1)

    assertion_1 = {
        "downstream": {"__ROOT__:__ROOT__.email"},
        "upstream": {"postgres_example_test_dataset:employee.employee_id"},
    }
    assert (
        assertion_1 == references["postgres_example_test_dataset:visit.email"]
    ), references["postgres_example_test_dataset:visit.email"]
