"""
Lottery System with Modern GUI Interface
A complete lottery game with ticket purchasing, draw results, and statistics
"""

import random
import json
import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter.font import Font
from PIL import Image, ImageTk  # You may need to install: pip install Pillow


class LotteryTicket:
    """Represents a single lottery ticket with 6 unique numbers (1-49)."""
    
    def __init__(self, numbers: List[int]):
        if len(numbers) != 6:
            raise ValueError("Ticket must have exactly 6 numbers")
        if len(set(numbers)) != 6:
            raise ValueError("Ticket numbers must be unique")
        if not all(1 <= n <= 49 for n in numbers):
            raise ValueError("All numbers must be between 1 and 49")
        
        self.numbers = sorted(numbers)
        self.purchase_time = datetime.now()
    
    def __repr__(self):
        return f"Ticket({self.numbers})"
    
    def to_dict(self):
        return {
            "numbers": self.numbers,
            "purchase_time": self.purchase_time.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        ticket = cls(data["numbers"])
        ticket.purchase_time = datetime.fromisoformat(data["purchase_time"])
        return ticket


class LotteryDraw:
    """Represents a lottery draw with winning numbers and prize distribution."""
    
    PRIZE_TIERS = [
        (6, False, "Jackpot", 0.5),
        (5, True, "Match 5 + Bonus", 0.1),
        (5, False, "Match 5", 0.05),
        (4, False, "Match 4", 0.02),
        (3, False, "Match 3", 0.01),
    ]
    
    FIXED_MATCH_3_PRIZE = 10
    
    def __init__(self):
        self.main_numbers = self._generate_numbers()
        self.bonus_number = random.randint(1, 49)
        while self.bonus_number in self.main_numbers:
            self.bonus_number = random.randint(1, 49)
        self.draw_date = datetime.now()
        self.total_tickets = 0
        self.ticket_sales = []
    
    @staticmethod
    def _generate_numbers():
        return sorted(random.sample(range(1, 50), 6))
    
    def add_ticket(self, ticket: LotteryTicket):
        self.ticket_sales.append(ticket)
        self.total_tickets += 1
    
    def check_ticket(self, ticket: LotteryTicket):
        matching_main = len(set(ticket.numbers) & set(self.main_numbers))
        bonus_matched = self.bonus_number in ticket.numbers
        return matching_main, bonus_matched
    
    def calculate_winnings(self, ticket: LotteryTicket, prize_pool: float):
        matching_main, bonus_matched = self.check_ticket(ticket)
        
        if matching_main == 3:
            return self.FIXED_MATCH_3_PRIZE
        
        for main_match, need_bonus, _, multiplier in self.PRIZE_TIERS:
            if matching_main == main_match:
                if need_bonus and not bonus_matched:
                    continue
                return prize_pool * multiplier
        
        return 0.0
    
    def get_winning_numbers(self):
        return {
            "main_numbers": self.main_numbers,
            "bonus_number": self.bonus_number,
            "draw_date": self.draw_date.isoformat()
        }
    
    def to_dict(self):
        return {
            "main_numbers": self.main_numbers,
            "bonus_number": self.bonus_number,
            "draw_date": self.draw_date.isoformat(),
            "total_tickets": self.total_tickets,
            "ticket_sales": [t.to_dict() for t in self.ticket_sales]
        }
    
    @classmethod
    def from_dict(cls, data):
        draw = cls.__new__(cls)
        draw.main_numbers = data["main_numbers"]
        draw.bonus_number = data["bonus_number"]
        draw.draw_date = datetime.fromisoformat(data["draw_date"])
        draw.total_tickets = data["total_tickets"]
        draw.ticket_sales = [LotteryTicket.from_dict(t) for t in data["ticket_sales"]]
        return draw


class LotteryGame:
    """Main lottery game controller."""
    
    TICKET_PRICE = 2.0
    DATA_FILE = "lottery_data.json"
    
    def __init__(self):
        self.jackpot = 0.0
        self.current_draw = LotteryDraw()
        self.past_draws = []
        self.load_data()
    
    def purchase_ticket(self, numbers: Optional[List[int]] = None):
        if numbers is None:
            numbers = LotteryDraw._generate_numbers()
        
        ticket = LotteryTicket(numbers)
        self.current_draw.add_ticket(ticket)
        prize_pool_contribution = self.TICKET_PRICE * 0.5
        self.jackpot += prize_pool_contribution
        return ticket
    
    def generate_random_ticket(self):
        return self.purchase_ticket()
    
    def perform_draw(self):
        if self.current_draw.total_tickets == 0:
            raise ValueError("No tickets sold for this draw!")
        
        total_prize_pool = self.jackpot
        winners = []
        ticket_results = []
        
        for ticket in self.current_draw.ticket_sales:
            matching_main, bonus_matched = self.current_draw.check_ticket(ticket)
            winnings = self.current_draw.calculate_winnings(ticket, total_prize_pool)
            
            if winnings > 0:
                winners.append({
                    "ticket": ticket,
                    "matching": matching_main,
                    "bonus": bonus_matched,
                    "winnings": winnings
                })
                total_prize_pool -= winnings
            
            ticket_results.append({
                "numbers": ticket.numbers,
                "matching_main": matching_main,
                "bonus_matched": bonus_matched,
                "winnings": winnings
            })
        
        winners.sort(key=lambda x: x["winnings"], reverse=True)
        prizes_paid = sum(w["winnings"] for w in winners)
        
        draw_record = {
            "draw": self.current_draw,
            "date": datetime.now(),
            "total_tickets": self.current_draw.total_tickets,
            "ticket_sales": self.current_draw.ticket_sales,
            "winning_numbers": self.current_draw.get_winning_numbers(),
            "winners": winners,
            "jackpot_before": self.jackpot,
            "prizes_paid": prizes_paid,
            "remaining_pool": total_prize_pool
        }
        
        self.past_draws.append(draw_record)
        self.jackpot = total_prize_pool if total_prize_pool > 0 else 0
        self.current_draw = LotteryDraw()
        self.save_data()
        
        return {
            "winning_numbers": draw_record["winning_numbers"]["main_numbers"],
            "bonus": draw_record["winning_numbers"]["bonus_number"],
            "total_tickets": draw_record["total_tickets"],
            "jackpot": draw_record["jackpot_before"],
            "winners": winners,
            "prizes_paid": prizes_paid,
            "new_jackpot": self.jackpot,
            "ticket_results": ticket_results
        }
    
    def get_statistics(self):
        total_tickets_sold = sum(d["total_tickets"] for d in self.past_draws)
        total_draws = len(self.past_draws)
        total_prizes_paid = sum(d["prizes_paid"] for d in self.past_draws)
        
        all_numbers = []
        for draw in self.past_draws:
            for ticket in draw["ticket_sales"]:
                all_numbers.extend(ticket.numbers)
        
        number_frequency = {}
        for num in all_numbers:
            number_frequency[num] = number_frequency.get(num, 0) + 1
        
        most_common = sorted(number_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_draws": total_draws,
            "total_tickets_sold": total_tickets_sold,
            "total_revenue": total_tickets_sold * self.TICKET_PRICE,
            "total_prizes_paid": total_prizes_paid,
            "current_jackpot": self.jackpot,
            "most_common_numbers": most_common
        }
    
    def save_data(self):
        data = {
            "jackpot": self.jackpot,
            "current_draw": self.current_draw.to_dict(),
            "past_draws": [d["draw"].to_dict() for d in self.past_draws]
        }
        with open(self.DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_data(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, 'r') as f:
                    data = json.load(f)
                self.jackpot = data["jackpot"]
                self.current_draw = LotteryDraw.from_dict(data["current_draw"])
                self.past_draws = [{"draw": LotteryDraw.from_dict(d)} for d in data["past_draws"]]
            except:
                pass


class LotteryGUI:
    """Modern GUI for the Lottery Game"""
    
    def __init__(self):
        self.game = LotteryGame()
        self.root = tk.Tk()
        self.root.title("🎰 Lottery System")
        self.root.geometry("1200x700")
        self.root.configure(bg='#2c3e50')
        
        # Configure styles
        self.setup_styles()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_purchase_tab()
        self.create_draw_tab()
        self.create_statistics_tab()
        self.create_history_tab()
        
        # Update dashboard
        self.update_dashboard()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure custom styles for widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'), foreground='#e74c3c')
        style.configure('Jackpot.TLabel', font=('Helvetica', 18, 'bold'), foreground='#f39c12')
        style.configure('Info.TLabel', font=('Helvetica', 10), background='#ecf0f1')
        style.configure('Success.TButton', font=('Helvetica', 10, 'bold'), background='#27ae60')
        style.configure('Danger.TButton', font=('Helvetica', 10, 'bold'), background='#e74c3c')
        
        # Configure frames
        style.configure('Card.TFrame', background='white', relief='raised', borderwidth=1)
        style.configure('Dark.TFrame', background='#34495e')
    
    def create_dashboard_tab(self):
        """Create the main dashboard tab"""
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text='📊 Dashboard')
        
        # Title
        title = ttk.Label(self.dashboard_frame, text='Lottery System', style='Title.TLabel')
        title.pack(pady=20)
        
        # Jackpot card
        jackpot_card = tk.Frame(self.dashboard_frame, bg='white', relief='raised', bd=2)
        jackpot_card.pack(pady=20, padx=50, fill='x')
        
        ttk.Label(jackpot_card, text='CURRENT JACKPOT', font=('Helvetica', 14), 
                  background='white').pack(pady=10)
        self.jackpot_label = ttk.Label(jackpot_card, text='$0.00', 
                                       font=('Helvetica', 32, 'bold'), foreground='#e74c3c')
        self.jackpot_label.pack(pady=10)
        
        # Statistics cards frame
        stats_frame = tk.Frame(self.dashboard_frame, bg='#2c3e50')
        stats_frame.pack(pady=20, padx=50, fill='x')
        
        # Create cards
        cards = [
            ('🎫', 'Total Tickets', 'total_tickets'),
            ('💰', 'Total Revenue', 'total_revenue'),
            ('🏆', 'Total Winners', 'total_winners'),
            ('📅', 'Total Draws', 'total_draws')
        ]
        
        self.stats_labels = {}
        for i, (icon, title, key) in enumerate(cards):
            card = tk.Frame(stats_frame, bg='white', relief='raised', bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            stats_frame.grid_columnconfigure(i, weight=1)
            
            ttk.Label(card, text=icon, font=('Helvetica', 24), background='white').pack(pady=5)
            ttk.Label(card, text=title, font=('Helvetica', 10), background='white').pack()
            label = ttk.Label(card, text='0', font=('Helvetica', 16, 'bold'), 
                              background='white', foreground='#3498db')
            label.pack(pady=5)
            self.stats_labels[key] = label
        
        # Recent activity
        recent_frame = tk.Frame(self.dashboard_frame, bg='white', relief='raised', bd=1)
        recent_frame.pack(pady=20, padx=50, fill='both', expand=True)
        
        ttk.Label(recent_frame, text='Recent Activity', font=('Helvetica', 14, 'bold'),
                  background='white').pack(pady=10)
        
        self.recent_text = scrolledtext.ScrolledText(recent_frame, height=10, width=60,
                                                       font=('Courier', 10))
        self.recent_text.pack(padx=10, pady=10, fill='both', expand=True)
    
    def create_purchase_tab(self):
        """Create ticket purchase tab"""
        self.purchase_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.purchase_frame, text='🎟️ Buy Tickets')
        
        # Quick pick section
        quick_frame = tk.Frame(self.purchase_frame, bg='white', relief='raised', bd=1)
        quick_frame.pack(pady=20, padx=50, fill='x')
        
        ttk.Label(quick_frame, text='Quick Pick', font=('Helvetica', 14, 'bold'),
                  background='white').pack(pady=10)
        
        ttk.Button(quick_frame, text='Generate Random Ticket', 
                   command=self.generate_random_ticket,
                   style='Success.TButton').pack(pady=10)
        
        # Custom numbers section
        custom_frame = tk.Frame(self.purchase_frame, bg='white', relief='raised', bd=1)
        custom_frame.pack(pady=20, padx=50, fill='x')
        
        ttk.Label(custom_frame, text='Custom Numbers', font=('Helvetica', 14, 'bold'),
                  background='white').pack(pady=10)
        
        # Number selection buttons
        numbers_frame = tk.Frame(custom_frame, bg='white')
        numbers_frame.pack(pady=10)
        
        self.selected_numbers = []
        self.number_buttons = []
        
        # Create number buttons 1-49 in a grid
        for i in range(1, 50):
            btn = tk.Button(numbers_frame, text=str(i), width=3, height=1,
                           bg='#ecf0f1', command=lambda x=i: self.toggle_number(x))
            btn.grid(row=(i-1)//7, column=(i-1)%7, padx=2, pady=2)
            self.number_buttons.append(btn)
        
        self.selected_label = ttk.Label(custom_frame, text='Selected: None', 
                                        background='white')
        self.selected_label.pack(pady=5)
        
        # Action buttons
        btn_frame = tk.Frame(custom_frame, bg='white')
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text='Clear Selection', 
                   command=self.clear_selection).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Purchase Ticket', 
                   command=self.purchase_custom_ticket,
                   style='Success.TButton').pack(side='left', padx=5)
        
        # Current tickets display
        tickets_frame = tk.Frame(self.purchase_frame, bg='white', relief='raised', bd=1)
        tickets_frame.pack(pady=20, padx=50, fill='both', expand=True)
        
        ttk.Label(tickets_frame, text='Current Draw Tickets', 
                  font=('Helvetica', 12, 'bold'), background='white').pack(pady=10)
        
        self.tickets_text = scrolledtext.ScrolledText(tickets_frame, height=8,
                                                        font=('Courier', 10))
        self.tickets_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        self.update_tickets_display()
    
    def create_draw_tab(self):
        """Create lottery draw tab"""
        self.draw_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.draw_frame, text='🎲 Perform Draw')
        
        # Draw info
        info_frame = tk.Frame(self.draw_frame, bg='white', relief='raised', bd=1)
        info_frame.pack(pady=20, padx=50, fill='x')
        
        ttk.Label(info_frame, text='Draw Information', font=('Helvetica', 14, 'bold'),
                  background='white').pack(pady=10)
        
        self.draw_info_text = scrolledtext.ScrolledText(info_frame, height=5,
                                                          font=('Courier', 10))
        self.draw_info_text.pack(padx=10, pady=10, fill='x')
        
        # Draw button
        ttk.Button(self.draw_frame, text='CONDUCT DRAW', 
                   command=self.perform_draw,
                   style='Danger.TButton').pack(pady=20)
        
        # Results display
        results_frame = tk.Frame(self.draw_frame, bg='white', relief='raised', bd=1)
        results_frame.pack(pady=20, padx=50, fill='both', expand=True)
        
        ttk.Label(results_frame, text='Draw Results', font=('Helvetica', 14, 'bold'),
                  background='white').pack(pady=10)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10,
                                                        font=('Courier', 10))
        self.results_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        self.update_draw_info()
    
    def create_statistics_tab(self):
        """Create statistics tab"""
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text='📈 Statistics')
        
        # Statistics display
        stats_display = tk.Frame(self.stats_frame, bg='white', relief='raised', bd=1)
        stats_display.pack(pady=20, padx=50, fill='both', expand=True)
        
        ttk.Label(stats_display, text='Lottery Statistics', font=('Helvetica', 16, 'bold'),
                  background='white').pack(pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_display, height=20,
                                                      font=('Courier', 10))
        self.stats_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        # Refresh button
        ttk.Button(self.stats_frame, text='Refresh Statistics',
                   command=self.refresh_statistics).pack(pady=10)
        
        self.refresh_statistics()
    
    def create_history_tab(self):
        """Create draw history tab"""
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text='📜 History')
        
        # History display
        history_display = tk.Frame(self.history_frame, bg='white', relief='raised', bd=1)
        history_display.pack(pady=20, padx=50, fill='both', expand=True)
        
        ttk.Label(history_display, text='Past Draws History', font=('Helvetica', 16, 'bold'),
                  background='white').pack(pady=10)
        
        self.history_text = scrolledtext.ScrolledText(history_display, height=20,
                                                        font=('Courier', 10))
        self.history_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        # Refresh button
        ttk.Button(self.history_frame, text='Refresh History',
                   command=self.refresh_history).pack(pady=10)
        
        self.refresh_history()
    
    def toggle_number(self, number):
        """Toggle number selection for custom ticket"""
        if number in self.selected_numbers:
            self.selected_numbers.remove(number)
        elif len(self.selected_numbers) < 6:
            self.selected_numbers.append(number)
        else:
            messagebox.showwarning("Limit Reached", "You can only select 6 numbers!")
            return
        
        # Update button colors
        for btn in self.number_buttons:
            num = int(btn['text'])
            if num in self.selected_numbers:
                btn.configure(bg='#3498db', fg='white')
            else:
                btn.configure(bg='#ecf0f1', fg='black')
        
        # Update label
        if self.selected_numbers:
            self.selected_label.config(text=f'Selected: {sorted(self.selected_numbers)}')
        else:
            self.selected_label.config(text='Selected: None')
    
    def clear_selection(self):
        """Clear number selection"""
        self.selected_numbers.clear()
        for btn in self.number_buttons:
            btn.configure(bg='#ecf0f1', fg='black')
        self.selected_label.config(text='Selected: None')
    
    def generate_random_ticket(self):
        """Generate and purchase a random ticket"""
        try:
            ticket = self.game.purchase_ticket()
            messagebox.showinfo("Success", 
                               f"Ticket purchased!\nNumbers: {ticket.numbers}\n"
                               f"Cost: ${self.game.TICKET_PRICE:.2f}")
            self.update_dashboard()
            self.update_tickets_display()
            self.update_draw_info()
            self.add_activity(f"Purchased random ticket: {ticket.numbers}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def purchase_custom_ticket(self):
        """Purchase a custom ticket"""
        if len(self.selected_numbers) != 6:
            messagebox.showwarning("Invalid Selection", 
                                  "Please select exactly 6 numbers (1-49)")
            return
        
        try:
            ticket = self.game.purchase_ticket(self.selected_numbers)
            messagebox.showinfo("Success", 
                               f"Ticket purchased!\nNumbers: {ticket.numbers}\n"
                               f"Cost: ${self.game.TICKET_PRICE:.2f}")
            self.clear_selection()
            self.update_dashboard()
            self.update_tickets_display()
            self.update_draw_info()
            self.add_activity(f"Purchased custom ticket: {ticket.numbers}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def perform_draw(self):
        """Perform the lottery draw"""
        if self.game.current_draw.total_tickets == 0:
            messagebox.showwarning("No Tickets", "No tickets sold for this draw!")
            return
        
        try:
            results = self.game.perform_draw()
            
            # Display results
            result_text = f"""
{'='*50}
DRAW RESULTS
{'='*50}
Winning Numbers: {results['winning_numbers']}
Bonus Number: {results['bonus']}
Total Tickets: {results['total_tickets']}
Jackpot: ${results['jackpot']:.2f}
Prizes Paid: ${results['prizes_paid']:.2f}
New Jackpot: ${results['new_jackpot']:.2f}

WINNERS:
{'-'*50}
"""
            if results['winners']:
                for winner in results['winners']:
                    result_text += f"Ticket {winner['ticket'].numbers}\n"
                    result_text += f"  Match {winner['matching']}"
                    if winner['bonus']:
                        result_text += " + Bonus"
                    result_text += f" - Won ${winner['winnings']:.2f}\n"
            else:
                result_text += "No winners this time! Jackpot rolls over.\n"
            
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(1.0, result_text)
            
            messagebox.showinfo("Draw Complete", 
                               f"Draw completed!\n"
                               f"Winning Numbers: {results['winning_numbers']}\n"
                               f"Bonus: {results['bonus']}\n"
                               f"Winners: {len(results['winners'])}\n"
                               f"Prizes Paid: ${results['prizes_paid']:.2f}")
            
            self.update_dashboard()
            self.update_tickets_display()
            self.update_draw_info()
            self.refresh_statistics()
            self.refresh_history()
            self.add_activity(f"Draw conducted - Winners: {len(results['winners'])}")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def update_dashboard(self):
        """Update dashboard statistics"""
        stats = self.game.get_statistics()
        
        # Update jackpot
        self.jackpot_label.config(f"${self.game.jackpot:.2f}")
        
        # Update statistics cards
        self.stats_labels['total_tickets'].config(str(stats['total_tickets_sold']))
        self.stats_labels['total_revenue'].config(f"${stats['total_revenue']:.2f}")
        
        # Calculate total winners
        total_winners = sum(len(d['winners']) for d in self.game.past_draws)
        self.stats_labels['total_winners'].config(str(total_winners))
        self.stats_labels['total_draws'].config(str(stats['total_draws']))
    
    def update_tickets_display(self):
        """Update current tickets display"""
        self.tickets_text.delete(1.0, tk.END)
        if self.game.current_draw.total_tickets == 0:
            self.tickets_text.insert(1.0, "No tickets purchased for current draw.")
        else:
            for i, ticket in enumerate(self.game.current_draw.ticket_sales, 1):
                self.tickets_text.insert(tk.END, f"{i:2d}. {ticket.numbers}\n")
    
    def update_draw_info(self):
        """Update draw information"""
        self.draw_info_text.delete(1.0, tk.END)
        info = f"""
Current Draw Information:
{'-'*40}
Draw Date: {self.game.current_draw.draw_date.strftime('%Y-%m-%d %H:%M')}
Tickets Sold: {self.game.current_draw.total_tickets}
Current Jackpot: ${self.game.jackpot:.2f}
Ticket Price: ${self.game.TICKET_PRICE:.2f}
"""
        self.draw_info_text.insert(1.0, info)
    
    def refresh_statistics(self):
        """Refresh statistics display"""
        stats = self.game.get_statistics()
        
        stat_text = f"""
LOTTERY STATISTICS
{'='*50}

Overall Statistics:
{'-'*40}
Total Draws: {stats['total_draws']}
Total Tickets Sold: {stats['total_tickets_sold']}
Total Revenue: ${stats['total_revenue']:.2f}
Total Prizes Paid: ${stats['total_prizes_paid']:.2f}
Current Jackpot: ${stats['current_jackpot']:.2f}

Prize Distribution:
{'-'*40}
Match 3: ${LotteryDraw.FIXED_MATCH_3_PRIZE:.2f} (fixed)
Match 4: Share of 2% of prize pool
Match 5: Share of 5% of prize pool
Match 5 + Bonus: Share of 10% of prize pool
Jackpot (Match 6): Share of 50% of prize pool

Most Common Numbers (All Time):
{'-'*40}
"""
        for num, freq in stats['most_common_numbers']:
            stat_text += f"Number {num:2d}: appeared {freq} times\n"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stat_text)
    
    def refresh_history(self):
        """Refresh draw history display"""
        self.history_text.delete(1.0, tk.END)
        
        if not self.game.past_draws:
            self.history_text.insert(1.0, "No draws have been conducted yet.")
            return
        
        for i, draw in enumerate(self.game.past_draws[-10:], 1):
            winning = draw['winning_numbers']
            history_entry = f"""
Draw {len(self.game.past_draws) - i + 1} - {draw['date'].strftime('%Y-%m-%d %H:%M')}
{'='*50}
Winning Numbers: {winning['main_numbers']} + Bonus {winning['bonus_number']}
Tickets Sold: {draw['total_tickets']}
Winners: {len(draw['winners'])}
Prizes Paid: ${draw['prizes_paid']:.2f}
Jackpot: ${draw['jackpot_before']:.2f}
{'-'*50}
"""
            self.history_text.insert(tk.END, history_entry)
    
    def add_activity(self, activity):
        """Add activity to recent activity log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.recent_text.insert(1.0, f"[{timestamp}] {activity}\n")
        # Keep only last 20 entries
        if int(self.recent_text.index('end-1c').split('.')[0]) > 20:
            self.recent_text.delete('20.0', 'end-1c')
    
    def on_closing(self):
        """Handle window closing"""
        self.game.save_data()
        self.root.destroy()
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = LotteryGUI()
    app.run()


if __name__ == "__main__":
    main()