from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner

import numpy as np
from pulp import *
import pandas as pd
import os

# ---------------- DÖNEM VERİSİ ----------------
periods = {
    "14 Gün": [130,50,180,80,30,50],
    "28 Gün": [110,40,200,100,35,55],
    "56 Gün": [90,30,230,130,40,60],
    "98 Gün": [70,20,250,160,45,65]
}

ferts = {
    "Urea":{"N":0.46,"P":0,"K":0,"Ca":0,"Mg":0,"S":0},
    "MAP":{"N":0.11,"P":0.52,"K":0,"Ca":0,"Mg":0,"S":0},
    "MKP":{"N":0,"P":0.52,"K":0.34,"Ca":0,"Mg":0,"S":0},
    "KNO3":{"N":0.13,"P":0,"K":0.46,"Ca":0,"Mg":0,"S":0},
    "CaNO3":{"N":0.15,"P":0,"K":0,"Ca":0.19,"Mg":0,"S":0},
    "MgSO4":{"N":0,"P":0,"K":0,"Ca":0,"Mg":0.098,"S":0.13},
    "K2SO4":{"N":0,"P":0,"K":0.50,"Ca":0,"Mg":0,"S":0.18}
}

class FertApp(App):

    def build(self):

        self.layout = BoxLayout(orientation="vertical")

        # ---------------- DÖNEM ----------------
        self.spinner = Spinner(
            text="14 Gün",
            values=list(periods.keys())
        )
        self.layout.add_widget(self.spinner)

        # ---------------- INPUT ----------------
        self.inputs = {}
        elements = ["N","P","K","Ca","Mg","S"]

        for e in elements:
            self.layout.add_widget(Label(text=e))
            ti = TextInput(text="0")
            self.inputs[e] = ti
            self.layout.add_widget(ti)

        # ---------------- FİYAT ----------------
        self.price = {}
        for f in ferts:
            self.layout.add_widget(Label(text=f+" fiyat"))
            ti = TextInput(text="5")
            self.price[f] = ti
            self.layout.add_widget(ti)

        # ---------------- BUTTON ----------------
        btn = Button(text="OPTİMİZE ET")
        btn.bind(on_press=self.solve)
        self.layout.add_widget(btn)

        # ---------------- RESULT ----------------
        self.result = Label(text="Sonuç")
        self.layout.add_widget(self.result)

        return self.layout

    def solve(self, instance):

        target = periods[self.spinner.text]

        N,P,K,Ca,Mg,S = target

        model = LpProblem("fert", LpMinimize)
        x = {f: LpVariable(f, 0) for f in ferts}

        cost = {f: float(self.price[f].text) for f in ferts}

        model += lpSum(cost[f]*x[f] for f in ferts)

        model += lpSum(ferts[f]["N"]*x[f] for f in ferts) == N
        model += lpSum(ferts[f]["P"]*x[f] for f in ferts) == P
        model += lpSum(ferts[f]["K"]*x[f] for f in ferts) == K
        model += lpSum(ferts[f]["Ca"]*x[f] for f in ferts) == Ca
        model += lpSum(ferts[f]["Mg"]*x[f] for f in ferts) == Mg
        model += lpSum(ferts[f]["S"]*x[f] for f in ferts) == S

        model.solve()

        out = ""

        for f in ferts:
            if x[f].varValue and x[f].varValue > 0:
                out += f"{f}: {round(x[f].varValue,2)}\n"

        # ---------------- EC ----------------
        total = sum(x[f].varValue or 0 for f in ferts)
        ec = total / 1000 * 1.2

        # ---------------- pH ----------------
        acid = 0
        for f in ferts:
            acid += (x[f].varValue or 0) * (1 if f in ["Urea","MAP","MKP"] else -1)

        ph = "Dengeli"
        if acid > 50:
            ph = "Asidik"
        elif acid < -50:
            ph = "Bazik"

        self.result.text = f"""
{out}

EC: {round(ec,2)}

pH: {ph}
"""

if __name__ == "__main__":
    FertApp().run()