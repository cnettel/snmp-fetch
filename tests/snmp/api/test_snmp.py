"""netframe::snmp::api snmp test cases."""

from typing import Sequence, cast

import hypothesis
import hypothesis.strategies as st
import pytest
from numpy.random import choice, seed

from snmp_fetch.snmp.api import Host, NullVarBind, PduType, SnmpErrorType, dispatch
from tests.snmp.strategies import (
    VALID_COMMUNITIES, VALID_HOSTNAMES, Config, communities, hosts, null_var_binds, oids, pdu_types
)


def sample2_null_var_binds(a: NullVarBind, b: NullVarBind) -> Sequence[NullVarBind]:
    """Sample two ambiguous NullVarBinds."""
    seed()
    return cast(Sequence[NullVarBind], choice([a, b], 2))


@hypothesis.given(
    pdu_type=pdu_types(),
    host_list=st.lists(hosts(), min_size=1, max_size=10),  # type: ignore
    var_binds=st.builds(
        lambda x, y: sample2_null_var_binds(x, NullVarBind(x.oid + y, 0, 0)),
        null_var_binds(),
        oids(min_size=0)
    )
)
@hypothesis.settings(
    deadline=None
)
def test_ambiguous_root_oids(
        pdu_type: PduType,
        host_list: Sequence[Host],
        var_binds: Sequence[NullVarBind]
) -> None:
    """Test ambiguous root oids."""
    with pytest.raises(ValueError):
        dispatch(pdu_type, host_list, var_binds)


@hypothesis.given(
    host_list=st.lists(hosts(  # type: ignore
        hostname=VALID_HOSTNAMES,
        community_list=st.lists(communities(string=VALID_COMMUNITIES), min_size=1, max_size=1),
        config=None
    ), min_size=1, max_size=10)
)
def test_no_such_instance(
        host_list: Sequence[Host]
) -> None:
    """Test no such instance."""
    results, errors = dispatch(
        PduType.GET, host_list, [NullVarBind([1], 0, 0)]
    )

    assert len(results) == 1
    assert results[0].size == 0
    assert len(errors) == len(host_list)
    for error in errors:
        assert error.type == SnmpErrorType.VALUE_WARNING
        assert error.message == 'NO_SUCH_INSTANCE'


@hypothesis.given(
    pdu_type=pdu_types([PduType.NEXT, PduType.BULKGET]),  # type: ignore
    host_list=st.lists(hosts(
        hostname=VALID_HOSTNAMES,
        community_list=st.lists(communities(string=VALID_COMMUNITIES), min_size=1, max_size=1),
        config=Config(bulk_repetitions=1)
    ), min_size=1, max_size=10)
)
def test_end_of_mib_view(
        pdu_type: PduType,
        host_list: Sequence[Host]
) -> None:
    """Test end of MIB view."""
    results, errors = dispatch(
        pdu_type, host_list, [NullVarBind([2, 0], 0, 0)]
    )

    assert len(results) == 1
    assert results[0].size == 0
    assert len(errors) == len(host_list)
    for error in errors:
        assert error.type == SnmpErrorType.VALUE_WARNING
        assert error.message == 'END_OF_MIB_VIEW'
