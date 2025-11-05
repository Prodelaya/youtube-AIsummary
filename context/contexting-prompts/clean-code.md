# 🎯 OBJETIVO
Cada fragmento de código o propuesta debe cumplir con los siguientes principios y guías:

---

## 🧹 REGLAS DE CLEAN CODE PARA PYTHON

### 1️⃣ NOMBRES CLAROS Y DESCRIPTIVOS
- Usa nombres expresivos en `snake_case` (funciones y variables) y `PascalCase` (clases).  
- Evita abreviaturas, siglas o letras sueltas.  
- Los nombres deben reflejar la intención, no el tipo.

---

### 2️⃣ FUNCIONES PEQUEÑAS Y CON UNA SOLA RESPONSABILIDAD
- Cada función debe hacer una única cosa y hacerlo bien.  
- Deben ser cortas, con un máximo de 20-30 líneas.  
- Nombres de función = acción concreta (ej: `obtener_datos_api()`, `calcular_promedio()`).

---

### 3️⃣ COMENTARIOS SOLO SI APORTAN CONTEXTO
- Usa comentarios solo para explicar decisiones no evidentes o dependencias externas.  
- Explica el *por qué*, no el *qué*.  
- Documenta con **docstrings** bien redactados en formato triple comillas `"""..."""`.

---

### 4️⃣ SIN DUPLICACIÓN (DRY: Don’t Repeat Yourself)
- No repitas código; extrae funciones o clases reutilizables.  
- Evita copiar y pegar bloques similares.

---

### 5️⃣ CLARIDAD > ASTUCIA
- Prefiere código legible antes que compacto o ingenioso.  
- Evita "one-liners" si sacrifican comprensión.

---

### 6️⃣ TIPADO Y DOCUMENTACIÓN
- Incluye anotaciones de tipo (`str`, `int`, `float`, `list`, etc.) en funciones y métodos.  
- Añade docstrings que describan parámetros, retorno y propósito.

---

### 7️⃣ MANEJO DE ERRORES LIMPIO
- Usa excepciones específicas (`FileNotFoundError`, `ValueError`, etc.).  
- Nunca uses `except:` vacío.  
- No ocultes errores; regístralos o notifícalos.

---

### 8️⃣ EVITA VALORES MÁGICOS
- Declara constantes con nombres en mayúsculas (`TIEMPO_ESPERA = 2`).  
- No uses números o cadenas sin contexto dentro del código.

---

### 9️⃣ ESTRUCTURA DE MÓDULOS LIMPIA
Orden recomendado del archivo:
1. Imports (agrupados y ordenados con **isort**)  
2. Constantes globales  
3. Clases  
4. Funciones  
5. Bloque principal (`if __name__ == "__main__":`)

---

### 🔟 FORMATO Y ESTILO (PEP 8)
- Usa sangría de 4 espacios.  
- No más de 80-100 caracteres por línea.  
- Espacios adecuados alrededor de operadores y comas.  
- Recomendado: formateo automático con **Black**.

---

## ⚙️ APLICACIÓN PRÁCTICA

Cuando generes código:
- Refactoriza automáticamente cualquier mal hábito o mala práctica.  
- Asegúrate de que el código sea **autoexplicativo** y con nombres coherentes.  
- Incluye **docstrings claros**, sin comentarios triviales.  
- Si el código es largo, divídelo en **módulos o funciones lógicas**.  
- Usa **tipado estático** y evita duplicaciones o bucles innecesarios.  
- Explica brevemente tus decisiones de diseño al final del bloque.  

---

## 📋 EJEMPLO DE ESTILO DE RESPUESTA

```python
def calcular_precio_total(precio_base: float, iva: float) -> float:
    """
    Calcula el precio total aplicando el IVA.

    :param precio_base: Precio sin impuestos
    :param iva: Porcentaje de IVA, por ejemplo 21.0
    :return: Precio final con IVA incluido
    """
    return precio_base * (1 + iva / 100)
