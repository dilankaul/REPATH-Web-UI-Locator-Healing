def test_algorithm_packages_expose_matchers() -> None:
    from repath_evaluation.algorithms import (
        WaterMatcher,
        VistaMatcher,
        SftmMatcher,
        WebEvoMatcher,
        SimiloMatcher,
    )
    from repath_evaluation.algorithms.water import WaterMatcher as DirectWaterMatcher
    from repath_evaluation.algorithms.vista import VistaMatcher as DirectVistaMatcher
    from repath_evaluation.algorithms.sftm import SftmMatcher as DirectSftmMatcher
    from repath_evaluation.algorithms.webevo import WebEvoMatcher as DirectWebEvoMatcher
    from repath_evaluation.algorithms.similo import SimiloMatcher as DirectSimiloMatcher

    assert WaterMatcher is DirectWaterMatcher
    assert VistaMatcher is DirectVistaMatcher
    assert SftmMatcher is DirectSftmMatcher
    assert WebEvoMatcher is DirectWebEvoMatcher
    assert SimiloMatcher is DirectSimiloMatcher
