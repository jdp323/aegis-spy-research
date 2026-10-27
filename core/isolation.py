"""Production boundaries reject tagged demonstration data recursively."""
def assert_real(value):
    if isinstance(value,dict):
        if value.get('model_generated') or value.get('model_feature_only'):raise ValueError('MODEL_DATA_FORBIDDEN_IN_REAL_STORE')
        if value.get('continuity_only'):raise ValueError('SYNTHETIC_CONTINUITY_FORBIDDEN')
        if value.get('feed_quality')=='SIMULATED' or value.get('entitlement')=='SIMULATED' or value.get('quality')=='SIMULATED':raise ValueError('SIMULATED_DATA_FORBIDDEN')
        for v in value.values():assert_real(v)
    elif isinstance(value,(list,tuple)):
        for v in value:assert_real(v)
