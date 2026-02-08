allerta_live = "VERDE"
        if temp_live >= 39 or vento_live >= 80: 
            allerta_live = "ROSSA"
        elif temp_live >= 36 or vento_live >= 60: 
            allerta_live = "ARANCIONE"
        elif temp_live >= 32 or vento_live >= 40: 
            allerta_live = "GIALLA"
        else: 
            allerta_live = "VERDE"