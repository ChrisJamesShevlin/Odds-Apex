import tkinter as tk
import math

def zip_probability(lam, k, p_zero=0.0):
    """
    Zero-inflated Poisson probability.
    p_zero is set to 0.0 to remove extra weighting for 0 goals.
    """
    if k == 0:
        return p_zero + (1 - p_zero) * math.exp(-lam)
    return (1 - p_zero) * ((lam ** k) * math.exp(-lam)) / math.factorial(k)

def calculate_insights():
    try:
        # --- 1) Retrieve all inputs ---
        avg_goals_home_scored   = float(entries["entry_home_scored"].get())
        avg_goals_home_conceded = float(entries["entry_home_conceded"].get())
        avg_goals_away_scored   = float(entries["entry_away_scored"].get())
        avg_goals_away_conceded = float(entries["entry_away_conceded"].get())
        
        injuries_home           = int(entries["entry_injuries_home"].get())
        injuries_away           = int(entries["entry_injuries_away"].get())
        position_home           = int(entries["entry_position_home"].get())
        position_away           = int(entries["entry_position_away"].get())
        form_home               = int(entries["entry_form_home"].get())
        form_away               = int(entries["entry_form_away"].get())
        
        home_xg_scored   = float(entries["entry_home_xg_scored"].get())
        away_xg_scored   = float(entries["entry_away_xg_scored"].get())
        home_xg_conceded = float(entries["entry_home_xg_conceded"].get())
        away_xg_conceded = float(entries["entry_away_xg_conceded"].get())
        
        # Live odds for Under/Over 2.5
        live_under_odds = float(entries["entry_live_under_odds"].get())
        live_over_odds  = float(entries["entry_live_over_odds"].get())
        
        # Live odds for match result (home win/draw/away win)
        live_home_odds = float(entries["entry_live_home_odds"].get())
        live_draw_odds = float(entries["entry_live_draw_odds"].get())
        live_away_odds = float(entries["entry_live_away_odds"].get())
        
        # --- 2) Calculate adjusted expected goals for each team ---
        adjusted_home_goals = ((avg_goals_home_scored + home_xg_scored +
                                avg_goals_away_conceded + away_xg_conceded) / 4)
        adjusted_home_goals *= (1 - 0.03 * injuries_home)
        adjusted_home_goals += form_home * 0.1 - position_home * 0.01
        
        adjusted_away_goals = ((avg_goals_away_scored + away_xg_scored +
                                avg_goals_home_conceded + home_xg_conceded) / 4)
        adjusted_away_goals *= (1 - 0.03 * injuries_away)
        adjusted_away_goals += form_away * 0.1 - position_away * 0.01
        
        # --- 3) Calculate scoreline probabilities (Poisson, up to 10 goals each) ---
        goal_range = 10
        scoreline_probs = {}
        for i in range(goal_range):
            for j in range(goal_range):
                p = zip_probability(adjusted_home_goals, i) * zip_probability(adjusted_away_goals, j)
                scoreline_probs[(i, j)] = p
        
        # --- 4) Top 4 most likely scorelines ---
        sorted_scorelines = sorted(scoreline_probs.items(), key=lambda x: x[1], reverse=True)
        top4 = sorted_scorelines[:4]
        
        # --- 5) Total goals distribution (0–6) ---
        total_goals_distribution = {}
        for (i, j), p in scoreline_probs.items():
            tot = i + j
            total_goals_distribution[tot] = total_goals_distribution.get(tot, 0) + p
        
        # --- 6) Calculate match result probabilities from scorelines ---
        model_home_win = sum(p for (i, j), p in scoreline_probs.items() if i > j)
        model_draw     = sum(p for (i, j), p in scoreline_probs.items() if i == j)
        model_away_win = sum(p for (i, j), p in scoreline_probs.items() if i < j)
        
        # --- 7) Blend match result model probabilities with live odds ---
        live_home_prob = 1 / live_home_odds if live_home_odds > 0 else 0
        live_draw_prob = 1 / live_draw_odds if live_draw_odds > 0 else 0
        live_away_prob = 1 / live_away_odds if live_away_odds > 0 else 0
        
        sum_live = live_home_prob + live_draw_prob + live_away_prob
        if sum_live > 0:
            live_home_prob /= sum_live
            live_draw_prob /= sum_live
            live_away_prob /= sum_live
        
        blend_factor = 0.3  # 30% from live, 70% from model
        final_home_win = model_home_win * (1 - blend_factor) + live_home_prob * blend_factor
        final_draw     = model_draw     * (1 - blend_factor) + live_draw_prob * blend_factor
        final_away_win = model_away_win * (1 - blend_factor) + live_away_prob * blend_factor
        
        sum_final = final_home_win + final_draw + final_away_win
        if sum_final > 0:
            final_home_win /= sum_final
            final_draw     /= sum_final
            final_away_win /= sum_final
        
        # --- 8) Under/Over 2.5 goals probabilities ---
        under_prob_model = 0.0
        for i in range(goal_range):
            for j in range(goal_range):
                if (i + j) <= 2:
                    under_prob_model += zip_probability(adjusted_home_goals, i) * zip_probability(adjusted_away_goals, j)
        over_prob_model = 1 - under_prob_model
        
        live_under_prob = 1 / live_under_odds if live_under_odds > 0 else 0
        live_over_prob  = 1 / live_over_odds  if live_over_odds > 0 else 0
        sum_live_ou = live_under_prob + live_over_prob
        if sum_live_ou > 0:
            live_under_prob /= sum_live_ou
            live_over_prob  /= sum_live_ou
        
        final_under_prob = under_prob_model * (1 - blend_factor) + live_under_prob * blend_factor
        final_over_prob  = over_prob_model  * (1 - blend_factor) + live_over_prob  * blend_factor
        sum_final_ou = final_under_prob + final_over_prob
        if sum_final_ou > 0:
            final_under_prob /= sum_final_ou
            final_over_prob  /= sum_final_ou
        
        # --- 9) Compute fair odds for everything ---
        def fair_odds(prob):
            return (1/prob) if prob > 0 else float('inf')
        
        # Scoreline fair odds (for top 4)
        # We'll just do 1 / that scoreline probability
        # If prob is 0, we do 'inf'
        
        # Match results
        odds_home = fair_odds(final_home_win)
        odds_draw = fair_odds(final_draw)
        odds_away = fair_odds(final_away_win)
        
        # Over/Under
        odds_under = fair_odds(final_under_prob)
        odds_over  = fair_odds(final_over_prob)
        
        # --- 10) Build final output text ---
        out_text = "=== Match Insights ===\n\n"
        
        # Top 4 scorelines
        out_text += "Top 4 Likely Scorelines:\n"
        for (score, prob) in top4:
            score_odds = fair_odds(prob)
            out_text += f"{score[0]} - {score[1]}: {prob*100:.1f}% (Odds: {score_odds:.2f})\n"
        out_text += "\n"
        
        # Total goals distribution
        out_text += "Total Goals Distribution (0–6):\n"
        for tot in range(0, 7):
            p = total_goals_distribution.get(tot, 0)
            pct = p * 100
            odds_tg = fair_odds(p)
            out_text += f"{tot} goals: {pct:.1f}% (Odds: {odds_tg:.2f})\n"
        out_text += "\n"
        
        # Match results
        out_text += "Match Results:\n"
        out_text += f"Home Win: {final_home_win*100:.1f}% (Odds: {odds_home:.2f})\n"
        out_text += f"Draw: {final_draw*100:.1f}% (Odds: {odds_draw:.2f})\n"
        out_text += f"Away Win: {final_away_win*100:.1f}% (Odds: {odds_away:.2f})\n\n"
        
        # Over 2.5 goals
        out_text += "Over 2.5 Goals:\n"
        out_text += f"{final_over_prob*100:.1f}% (Odds: {odds_over:.2f})\n"
        
        # --- 11) Display the results in the text widget ---
        result_text_widget.delete("1.0", tk.END)
        result_text_widget.insert(tk.END, out_text)
        
    except ValueError:
        result_text_widget.delete("1.0", tk.END)
        result_text_widget.insert(tk.END, "Please enter valid numerical values.")

def reset_fields():
    for entry in entries.values():
        entry.delete(0, tk.END)
    result_text_widget.delete("1.0", tk.END)

# --- GUI Layout ---
root = tk.Tk()
root.title("Odds Apex - Prematch")

# Define input fields
entries = {
    "entry_home_scored":      tk.Entry(root),
    "entry_home_conceded":    tk.Entry(root),
    "entry_away_scored":      tk.Entry(root),
    "entry_away_conceded":    tk.Entry(root),
    "entry_injuries_home":    tk.Entry(root),
    "entry_injuries_away":    tk.Entry(root),
    "entry_position_home":    tk.Entry(root),
    "entry_position_away":    tk.Entry(root),
    "entry_form_home":        tk.Entry(root),
    "entry_form_away":        tk.Entry(root),
    "entry_home_xg_scored":   tk.Entry(root),
    "entry_away_xg_scored":   tk.Entry(root),
    "entry_home_xg_conceded": tk.Entry(root),
    "entry_away_xg_conceded": tk.Entry(root),
    "entry_live_under_odds":  tk.Entry(root),
    "entry_live_over_odds":   tk.Entry(root),
    "entry_live_home_odds":   tk.Entry(root),
    "entry_live_draw_odds":   tk.Entry(root),
    "entry_live_away_odds":   tk.Entry(root),
}

labels_text = [
    "Avg Goals Home Scored", "Avg Goals Home Conceded", "Avg Goals Away Scored", "Avg Goals Away Conceded",
    "Injuries Home", "Injuries Away", "Position Home", "Position Away",
    "Form Home", "Form Away", "Home xG Scored", "Away xG Scored",
    "Home xG Conceded", "Away xG Conceded", "Live Under 2.5 Odds", "Live Over 2.5 Odds",
    "Live Home Win Odds", "Live Draw Odds", "Live Away Win Odds",
]

for i, (key, label_text) in enumerate(zip(entries.keys(), labels_text)):
    label = tk.Label(root, text=label_text)
    label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
    entries[key].grid(row=i, column=1, padx=5, pady=5)

# Create a frame for the output (with a white background and a scrollbar)
result_frame = tk.Frame(root)
result_frame.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
root.grid_rowconfigure(len(entries), weight=1)
root.grid_columnconfigure(1, weight=1)

result_text_widget = tk.Text(result_frame, wrap=tk.WORD, background="white", width=50, height=15)
result_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(result_frame, command=result_text_widget.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
result_text_widget.config(yscrollcommand=scrollbar.set)

calc_button = tk.Button(root, text="Calculate Match Insights", command=calculate_insights)
calc_button.grid(row=len(entries)+1, column=0, columnspan=2, padx=5, pady=10)

reset_button = tk.Button(root, text="Reset All Fields", command=reset_fields)
reset_button.grid(row=len(entries)+2, column=0, columnspan=2, padx=5, pady=10)

root.mainloop()
