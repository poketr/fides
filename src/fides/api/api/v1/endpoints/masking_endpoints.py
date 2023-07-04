from typing import Any, List

from fastapi import HTTPException, Security
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from fides.api.common_exceptions import NoSuchStrategyException, ValidationError
from fides.api.oauth.utils import verify_oauth_client_prod
from fides.api.schemas.masking.masking_api import MaskingAPIRequest, MaskingAPIResponse
from fides.api.schemas.masking.masking_strategy_description import (
    MaskingStrategyDescription,
)
from fides.api.schemas.policy import PolicyMaskingSpec
from fides.api.service.masking.strategy.masking_strategy import MaskingStrategy
from fides.api.util.api_router import APIRouter
from fides.common.api.scope_registry import MASKING_EXEC, MASKING_READ
from fides.common.api.v1.urn_registry import MASKING, MASKING_STRATEGY, V1_URL_PREFIX
from fides.logging import logger

router = APIRouter(tags=["Masking"], prefix=V1_URL_PREFIX)


@router.put(
    MASKING,
    response_model=MaskingAPIResponse,
    dependencies=[
        Security(
            verify_oauth_client_prod,
            scopes=[MASKING_EXEC],
        )
    ],
)
def mask_value(request: MaskingAPIRequest) -> MaskingAPIResponse:
    """Masks the value(s) provided using the provided masking strategy"""
    try:
        values: List[Any] = request.values
        masked_values: List[Any] = request.values.copy()
        masking_strategies: List[PolicyMaskingSpec] = request.masking_strategies

        num_strat: int = len(masking_strategies)

        if num_strat > 1:
            logger.info(
                "%s masking strategies requested; running in order.",
                num_strat,
            )

        for strategy in masking_strategies:
            masking_strategy = MaskingStrategy.get_strategy(
                strategy.strategy, strategy.configuration
            )
            logger.info(
                "Starting masking of %s value(s) with strategy %s",
                len(values),
                strategy.strategy,
            )
            masked_values = masking_strategy.mask(  # type: ignore
                masked_values, None
            )  # passing in masked values from previous strategy

        return MaskingAPIResponse(plain=values, masked_values=masked_values)
    except NoSuchStrategyException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    MASKING_STRATEGY,
    response_model=List[MaskingStrategyDescription],
    dependencies=[
        Security(
            verify_oauth_client_prod,
            scopes=[MASKING_READ],
        )
    ],
)
def list_masking_strategies() -> List[MaskingStrategyDescription]:
    """Lists available masking strategies with instructions on how to use them"""
    logger.info("Getting available masking strategies")
    return [strategy.get_description() for strategy in MaskingStrategy.get_strategies()]
