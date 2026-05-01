import tkinter as tk
from tkinter import filedialog, messagebox
from rembg import remove
from PIL import Image
import os

def processar_imagem():
    caminho_entrada = filedialog.askopenfilename(
        title="Selecione a imagem original",
        filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")]
    )
    
    if not caminho_entrada:
        return

    caminho_saida = filedialog.asksaveasfilename(
        title="Salvar imagem sem fundo como...",
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png")],
        initialfile="imagem_sem_fundo.png"
    )
    
    if not caminho_saida:
        return

    try:
        with open(caminho_entrada, 'rb') as i:
            input_data = i.read()
            output_data = remove(input_data)
            
        with open(caminho_saida, 'wb') as o:
            o.write(output_data)
            
        messagebox.showinfo("Sucesso", f"foi, salva ae:\n{caminho_saida}")
    
    except Exception as e:
        messagebox.showerror("Erro", f"Deu bronca: {e}")

root = tk.Tk()
root.title("Removedor de Fundo IA")
root.geometry("300x150")

label = tk.Label(root, text="Clique no botão para iniciar", pady=20)
label.pack()

btn = tk.Button(root, text="Selecionar Imagem", command=processar_imagem, 
                bg="#4CAF50", fg="white", padx=20, pady=10)
btn.pack()

root.mainloop()