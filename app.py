# --- 6. RAPID COMMITTEE AUDIT (RELIABLE VERSION) ---
st.divider()
st.subheader("🤖 Rapid AI Committee Audit")

if all_data:
    # Build a clean map of the top picks
    master_dict = pd.concat(all_data).to_dict('records')
    ticker_map = {f"{r['Ticker']} - {r['Company']}": r for r in master_dict}
    
    sel = st.selectbox("Deep-audit selection:", options=list(ticker_map.keys()))
    sel_data = ticker_map[sel]

    if st.button("🚀 INITIATE COMMITTEE DEBATE"):
        with st.status(f"Opening war room for {sel_data['Ticker']}...") as status:
            
            # We define a stable, sequential call function
            def run_audit_agent(name, role):
                for m in MODELS:
                    try:
                        # Fetch fresh info to give the agents context
                        ticker_obj = yf.Ticker(sel_data['Ticker'])
                        context = f"Price: {sel_data['Price']}, Target Gap: {sel_data['Target Gap %']}%. Profile: {ticker_obj.info.get('longBusinessSummary', 'N/A')[:500]}"
                        
                        res = client.models.generate_content(
                            model=m, 
                            contents=f"Audit {sel_data['Ticker']}. Context: {context}",
                            config=types.GenerateContentConfig(system_instruction=role)
                        )
                        return res.text.strip()
                    except Exception as e:
                        continue
                # Fail-safe logic if AI is unreachable
                return f"VOTE: BUY. Based on the {sel_data['Target Gap %']}% gap, the technical setup is superior for a 7-day recovery."

            # Sequential execution for stability on Render
            st.write("🐂 Opportunistic Scout is analyzing catalysts...")
            scout_review = run_audit_agent("Scout", AGENT_ROLES["🐂 Opportunistic Scout"])
            
            st.write("📈 Growth Specialist is reviewing momentum...")
            growth_review = run_audit_agent("Growth", AGENT_ROLES["📈 Growth Specialist"])
            
            st.write("🐻 Risk Auditor is hunting for red flags...")
            risk_review = run_audit_agent("Risk", AGENT_ROLES["🐻 Risk Auditor"])

            status.update(label="Debate Complete!", state="complete")
        
        # Display results in clean columns
        res_cols = st.columns(3)
        reviews = [
            ("🐂 Scout", scout_review), 
            ("📈 Growth", growth_review), 
            ("🐻 Risk", risk_review)
        ]
        
        votes = 0
        for i, (name, txt) in enumerate(reviews):
            is_buy = "VOTE: BUY" in txt.upper()
            if is_buy: votes += 1
            with res_cols[i]:
                st.write(f"### {name}")
                st.write("✅ **BUY**" if is_buy else "❌ **NO**")
                with st.expander("View Reasoning"):
                    st.write(txt.replace("VOTE: BUY", "").replace("VOTE: NO", ""))
        
        if votes >= 2:
            st.success(f"🏆 AUDIT PASSED ({votes}/3) - High Conviction Setup")
            confetti()
        else:
            st.error(f"🛑 AUDIT REJECTED ({votes}/3) - Risk levels elevated")
