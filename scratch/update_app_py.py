import os

filepath = "app.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "# 6. Advanced Fallback Dynamic Rule Engine (Zero-dependency Local AI)"
end_marker = 'return jsonify({"reply": reply})'

start_idx = content.find(start_marker)
if start_idx == -1:
    print("START MARKER NOT FOUND")
    exit(1)

end_idx = content.find(end_marker, start_idx)
if end_idx == -1:
    print("END MARKER NOT FOUND")
    exit(1)

replacement_block = """# 6. Advanced Fallback Dynamic Rule Engine (Zero-dependency Local AI)
        is_telugu = any(x in user_msg_lower for x in [
            "మార్కెట్", "పెరుగు", "తగ్గు", "ట్రాప్", "లెవెల్", "ఏమైంది", "ఏంటి", "పుట్", "కాల్", "నిఫ్టీ", "చెప్పు", "ఎలా", "హెవీ", "వాల్యూ", "డౌన్", "సపోర్ట్", "రెసిస్టెన్స్", "డెల్టా", "గ్యాప్", "రేపు", "ఓఐ", "ఎటు", "వెళ్తుంది", "పైకి", "కిందకి", "జీరో", "హీరో", "యాక్సిలరేషన్", "క్యాలిక్యులేషన్",
            "cheppu", "chappu", "enti", "chudu", "ekkada", "adi", "telugu", "cheppi", "chapp"
        ])
        reply = ""
        
        if is_telugu:
            # Check for GVN Formulas first
            if any(x in user_msg_lower for x in ["zero to hero", "zero-to-hero", "z2h", "జీరో", "హీరో", "formula 1", "formula1"]):
                reply = "సార్, జీరో-టు-హీరో (Formula 1) అనేది కేవలం ఎక్స్‌పైరీ రోజుల్లో పనిచేసే వ్యూహం. డెల్టా 0.40–0.50 స్ట్రైక్స్ లలో ధర మన బాటమ్ లెవెల్ i1 (Green Line) కు వచ్చినప్పుడు ఎంట్రీ తీసుకుంటాము. దీనికి 12 పాయింట్ల స్టాప్ లాస్ మరియు టార్గెట్స్ i7, i6, i5 గా ఉంటాయి సార్."
            elif any(x in user_msg_lower for x in ["level acceleration", "gamma squeeze", "gamma", "గామా", "యాక్సిలరేషన్", "formula 2", "formula2"]):
                reply = "సార్, GVN లెవెల్ యాక్సిలరేషన్ (Formula 2) అనేది ఇండెక్స్ 0.618 మరియు 0.50 లెవెల్స్ మధ్య ఉన్నప్పుడు పుట్ లేదా కాల్ ఆప్షన్స్ లో వచ్చే గామా స్క్వీజ్ కదలిక. ఆప్షన్ OTM నుండి ATM కి మారుతున్నప్పుడు గామా పీక్ (Peak Gamma) స్థాయికి చేరుకోవడం వల్ల ప్రీమియం అతివేగంగా దూసుకుపోతుంది. ఆప్షన్ Level 5 (ATM) దాటి ITM లోకి వెళ్ళినప్పుడు Gamma తగ్గి Delta 1.0 కి చేరుకుంటుంది, అప్పుడు ఆప్షన్ ధర ఇండెక్స్ తో పాటు 1:1 నిష్పత్తిలో దూసుకుపోతుంది సార్."
            elif any(x in user_msg_lower for x in ["status", "done", "complete", "పూర్తయిందా", "ముగిసిందా", "finished"]) and any(x in user_msg_lower for x in ["9:15", "9 15", "calculation", "క్యాలిక్యులేషన్"]):
                reply = f"సార్, ఈరోజు 9:15 AM నిఫ్టీ ఆప్షన్ లెవెల్స్ లెక్కించడం {'విజయవంతంగా పూర్తయింది సార్. అల్గో లైవ్ లో రన్ అవుతోంది.' if nifty_captured else 'ఇంకా పెండింగ్ లో ఉంది సార్. మార్కెట్ ఓపెన్ అయిన తర్వాత 9:15 AM క్యాండిల్ క్లోజ్ కోసం సిస్టమ్ వేచి చూస్తోంది.'}"
            elif any(x in user_msg_lower for x in ["9:15", "9 15", "క్యాలిక్యులేషన్", "formula 3", "formula3", "confirmation"]):
                reply = f"సార్, GVN 9:15 ఆప్షన్ లెవెల్ కన్ఫర్మేషన్ (Formula 3) లో 9:15 AM మొదటి క్యాండిల్ క్లోజ్ ఆధారంగా విండ్ డైరెక్షన్ కన్ఫర్మ్ చేస్తాము. కాల్ వైపు ఇండెక్స్ 0.618 పైన క్లోజ్ అయి, CE ఆప్షన్ 0.6 లెవెల్ ని తాకి, 0.5 లెవెల్ ని దాటిన తర్వాత మళ్ళీ 0.7 లేదా 0.6 లెవెల్ ని రీటెస్ట్ చేయాలి. పుట్ వైపు ఇండెక్స్ 0.5 కింద క్లోజ్ అయి, PE ఆప్షన్ 0.6 ని తాకి, రీటెస్ట్ చేసి 0.5 లేదా 0.7 లెవెల్స్ ని క్రాస్ చేయాలి. 10:45 వంటి ముఖ్యమైన సమయాల్లో కాల్ మరియు పుట్ లెవెల్స్ యొక్క దూరాన్ని పోల్చి చూస్తాము సార్. నిఫ్టీ క్యాలిక్యులేషన్స్ ప్రస్తుతం {'పూర్తయ్యాయి సార్' if nifty_captured else 'ఇంకా కాలేదు సార్'}."
            elif any(x in user_msg_lower for x in ["delta 60", "డెల్టా 60", "delta"]):
                reply = f"సార్, ఈరోజు డెల్టా 60 కాల్ స్ట్రైక్ ధర ₹{d60_ce} మరియు పుట్ స్ట్రైక్ ధర ₹{d60_pe} గా ఉన్నాయి. ప్రస్తుత నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f}."
            elif any(x in user_msg_lower for x in ["gap up", "gap down", "గ్యాప్", "గ్యాప్ అప్", "గ్యాప్ డౌన్", "tomorrow", "రేపు"]):
                if pcr > 1.15:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బుల్లిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-అప్ లేదా పాజిటివ్ ఓపెనింగ్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                elif pcr < 0.85:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బేరిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-డౌన్ లేదా బలహీనంగా ఓపెన్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                else:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} తటస్థంగా ఉంది. కాబట్టి రేపు మార్కెట్ ఫ్లాట్ లేదా చిన్న గ్యాప్ తో ఓపెన్ కావచ్చు సార్."
            elif any(x in user_msg_lower for x in ["highest oi", "హైయెస్ట్", "oi", "ఓ ఐ"]):
                reply = f"సార్, ఆప్షన్ చైన్ ఓపెన్ ఇంట్రెస్ట్ ప్రకారం, అత్యధిక కాల్ ఓఐ ₹{strong_resistance} వద్ద మరియు అత్యధిక పుట్ ఓఐ ₹{strong_support} వద్ద ఉంది. ఇది మార్కెట్ కి ముఖ్యమైన రేంజ్."
            elif any(x in user_msg_lower for x in ["upside", "downside", "direction", "ఎటు", "వెళ్తుంది", "పైకి", "కిందకి", "వాట్ అబౌట్", "what about"]):
                if pcr > 1.15 or trend == "BULLISH":
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బుల్లిష్ గా ఉంది. ఆప్షన్ చైన్ వాల్యూమ్స్ మరియు పిసిఆర్ ({pcr:.3f}) ఆధారంగా మార్కెట్ పైకి (upside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                elif pcr < 0.85 or trend == "BEARISH":
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బేరిష్ గా ఉంది. కాల్ రైటింగ్ అధికంగా ఉండటం వల్ల మార్కెట్ కిందకి (downside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                else:
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం సైడ్‌വേస్ లేదా కన్సాలిడేషన్ లో ఉంది. ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} వద్ద రేంజ్-బౌండ్ గా ఉంది సార్."
            elif any(x in user_msg_lower for x in ["పెరుగు", "కాల్", "ce", "పైకి"]):
                ce_data = next((x for x in scanner_items if f"{d60_ce} CE" in x.get("strike", "")), None)
                if not ce_data and ce_strikes:
                    ce_data = ce_strikes[0]
                if ce_data:
                    reply = f"సార్, {ce_data.get('strike')} కాల్ ఆప్షన్ యొక్క ప్రస్తుత ధర ₹{ce_data.get('ltp')}. దీని వాల్యూమ్ {ce_data.get('volume', 0):,} గా ఉంది. సిగ్నల్ {ce_data.get('ai_signal')} గా ఉంది."
                else:
                    reply = f"సార్, నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f} వద్ద ఉంది. కాల్స్ లో బలమైన కొనుగోలు ఇంకా కనిపించడం లేదు. పిసిఆర్ విలువ {pcr:.3f} గా ఉంది."
            elif any(x in user_msg_lower for x in ["తగ్గు", "పుట్", "pe", "కిందకి"]):
                pe_data = next((x for x in scanner_items if f"{d60_pe} PE" in x.get("strike", "")), None)
                if not pe_data and pe_strikes:
                    pe_data = pe_strikes[0]
                if pe_data:
                    reply = f"సార్, {pe_data.get('strike')} పుట్ ఆప్షన్ యొక్క ప్రస్తుత ధర ₹{pe_data.get('ltp')}. దీని వాల్యూమ్ {pe_data.get('volume', 0):,} గా ఉంది. సిగ్నల్ {pe_data.get('ai_signal')} గా ఉంది."
                else:
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బేరిష్ గా ఉంది. పిసిఆర్ విలువ {pcr:.3f} గా ఉంది. లెవెల్స్ ని గమనించి ట్రేడ్ చేయండి."
            elif any(x in user_msg_lower for x in ["ట్రాప్", "trap"]):
                reply = f"సార్, ప్రస్తుతం ఆప్షన్ చైన్ లో {trap_zone} మోడ్ కనిపిస్తోంది. స్మార్ట్ మనీ {smart_money} గా ఉంది. వాల్యూమ్ పెరగకుండా రిటైల్ బయర్స్ ను ట్రాప్ చేసే అవకాశం ఉంది, జాగ్రత్తగా ఉండండి."
            elif any(x in user_msg_lower for x in ["హెవీ", "వాల్యూ", "volume"]):
                ce_vol = sum(x.get("volume", 0) for x in ce_strikes[:3])
                pe_vol = sum(x.get("volume", 0) for x in pe_strikes[:3])
                if ce_vol > pe_vol:
                    reply = f"సార్, కాల్ ఆప్షన్స్ లో హెవీ వాల్యూమ్ ({ce_vol:,}) ఉంది. ఇది ఆపరేటర్లు కాల్ సైడ్ పొజిషన్స్ క్రియేట్ చేస్తున్నారని సూచిస్తుంది."
                else:
                    reply = f"సార్, పుట్ ఆప్షన్స్ లో వాల్యూమ్ అధికంగా ({pe_vol:,}) ఉంది. పుట్ సైడ్ అధిక ఆసక్తి కనిపిస్తోంది."
            elif any(x in user_msg_lower for x in ["లెవెల్", "level"]):
                i5_val = gvn_levels.get("i5", "N/A")
                i7_val = gvn_levels.get("i7", "N/A")
                reply = f"సార్, నిఫ్టీ 9:15 క్యాండిల్ ప్రకారం లెవెల్ 5 (i5) ₹{i5_val} మరియు లెవెల్ 7 (i7) ₹{i7_val} గా ఉన్నాయి. ధర ఈ లెవెల్స్ ని బ్రేక్ చేసినప్పుడు మాత్రమే ట్రేడ్ ప్లాన్ చేయండి."
            elif "9:15" in user_msg_lower:
                h_915 = gvn_levels.get("high_915", "N/A")
                l_915 = gvn_levels.get("low_915", "N/A")
                reply = f"సార్, నిఫ్టీ 9:15 బెంచ్‌మార్క్ హై ₹{h_915} మరియు లో ₹{l_915} గా రికార్డ్ అయింది. ఈ పరిధి దాటినప్పుడు మార్కెట్ కి ఒక డైరెక్షన్ లభిస్తుంది."
            else:
                reply = (
                    f"సార్, ప్రస్తుతం నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f} వద్ద ఉంది. "
                    f"సపోర్ట్ ₹{strong_support} మరియు రెసిస్టెన్స్ ₹{strong_resistance} గా ఉంది. "
                    f"మార్కెట్ ట్రెండ్ {trend} మరియు సెంట్రిమెంట్ {sentiment} గా ఉంది. పిసిఆర్ విలువ {pcr:.3f} వద్ద ఉంది."
                )
        else:
            # English Fallback specific questions
            if any(x in user_msg_lower for x in ["zero to hero", "zero-to-hero", "z2h", "formula 1", "formula1"]):
                reply = "Sir, GVN Expiry Zero-to-Hero (Formula 1) is an expiry-day only strategy. It selects strikes with Delta between 0.40 and 0.50. Entry is triggered when the premium drops near Level i1 (bottom Green Line / 1.0 Fib) and reverses, with a strict 12-point SL and targets at Levels i7, i6, and i5."
            elif any(x in user_msg_lower for x in ["level acceleration", "gamma squeeze", "gamma", "formula 2", "formula2"]):
                reply = "Sir, GVN Level Acceleration (Formula 2) is a Peak Gamma Squeeze strategy. When the index reverses between Level 6 (0.618 Fib) and Level 5 (0.50 Fib), the option premium explodes from Level 7 through Level 6 and 5 as OTM options transition to ATM, peaking Gamma. Above Level 5 (ITM), Delta approaches 1.0, moving 1:1 with the index towards Target Level 3, with a strict 12-point SL."
            elif any(x in user_msg_lower for x in ["status", "done", "complete", "finished"]) and any(x in user_msg_lower for x in ["9:15", "9 15", "calculation"]):
                reply = f"Sir, today's 9:15 AM option levels calculations are {'COMPLETED and the algo is running live.' if nifty_captured else 'PENDING. The system is waiting for the 9:15 AM opening candle to close.'}"
            elif any(x in user_msg_lower for x in ["9:15", "9 15", "calculation", "formula 3", "formula3", "confirmation"]):
                reply = f"Sir, GVN 9:15 Option Level Confirmation (Formula 3) validates morning retracements. For Call side (Bullish), the index closes above 0.618 Fib, and the Call option touches 0.6 level, crosses 0.5 level, and then retests 0.7 or 0.6. For Put side (Bearish), the index closes below 0.5 Fib, and the Put option touches 0.6, retests, and crosses 0.5 or 0.7. Time-based alignment (like comparing levels at 10:45 AM) confirms the direction. Calculations status: {'COMPLETED' if nifty_captured else 'PENDING'}."
            elif any(x in user_msg_lower for x in ["delta 60", "delta"]):
                reply = f"Sir, today's Delta 60 Call Strike is at {d60_ce} and Put Strike is at {d60_pe}. Spot is currently {nifty_spot:.2f}."
            elif any(x in user_msg_lower for x in ["gap up", "gap down", "tomorrow", "opening"]):
                if pcr > 1.15:
                    reply = f"Sir, PCR is {pcr:.3f} (Bullish). There is a high probability of tomorrow opening with a Gap-Up or positive start."
                elif pcr < 0.85:
                    reply = f"Sir, PCR is {pcr:.3f} (Bearish). There is a high probability of tomorrow opening with a Gap-Down or weak start."
                else:
                    reply = f"Sir, PCR is {pcr:.3f} (Neutral). Market is likely to open Flat or with a very minor gap tomorrow."
            elif any(x in user_msg_lower for x in ["highest oi", "highest open interest", "oi"]):
                reply = f"Sir, Calls highest OI/Volume is at {strong_resistance} and Puts highest OI/Volume is at {strong_support}."
            elif any(x in user_msg_lower for x in ["upside", "downside", "direction", "where", "go", "what about"]):
                if pcr > 1.15 or trend == "BULLISH":
                    reply = f"Sir, market is currently bullish with PCR {pcr:.3f}. Option chain indicates an upside target towards {strong_resistance}."
                elif pcr < 0.85 or trend == "BEARISH":
                    reply = f"Sir, market is currently bearish with PCR {pcr:.3f}. Call writers are strong, suggesting a downside move towards {strong_support}."
                else:
                    reply = f"Sir, market is range-bound and consolidating sideways (PCR: {pcr:.3f}). No clear direction yet."
            elif "nifty" in user_msg_lower or "spot" in user_msg_lower or "trend" in user_msg_lower:
                reply = f"Sir, Nifty spot is at {nifty_spot:.2f}. Support is at {strong_support} and Resistance is at {strong_resistance}. Trend is {trend}."
            elif "level" in user_msg_lower or "levels" in user_msg_lower:
                reply = f"Sir, current GVN i5 level is at {gvn_levels.get('i5', 'N/A')} and i7 is at {gvn_levels.get('i7', 'N/A')}."
            elif "trap" in user_msg_lower:
                reply = f"Sir, the option chain shows a {trap_zone} trap status. Smart money indicates {smart_money}."
            elif "volume" in user_msg_lower or "heavy" in user_msg_lower:
                reply = f"Sir, PCR is {pcr:.3f}. Call side vs Put side open interest is in a {sentiment} balance."
            else:
                reply = f"Hello Sir. Spot is at {nifty_spot:.2f}, Trend: {trend}, PCR: {pcr:.3f}. Support: {strong_support}, Resistance: {strong_resistance}."
                
        # Save chat messages to history
        gvn_data_bank.save_ai_message("user", user_msg)
        gvn_data_bank.save_ai_message("assistant", reply)
        """

new_content = content[:start_idx] + replacement_block + content[end_idx:]
with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)
print("REPLACEMENT SUCCESSFUL")
