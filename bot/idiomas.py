# Kabuzio web: the words of the watch pages and guides in each language (bot/paginas.py, bot/guias.py).
# Watch names stay as they are (English); everything around them is translated. English is the main site.
LANGS = ("en", "es", "fr", "de", "pt", "it")

T = {
    "en": {"all": "← All watches", "cta": "View deal on AliExpress", "bp": "AliExpress Buyer Protection", "ship": "Worldwide shipping",
           "picked": "Hand-picked best sellers", "sold": "{n}+ sold on AliExpress", "like": "You may also like",
           "desc": "{what} for {price} on AliExpress{sold}. Hand-picked by Kabuzio. Buyer Protection and worldwide shipping.",
           "watch": "watch", "soldshort": ", {n}+ sold", "more": "More watches every day on our",
           "social": "Telegram and social pages", "aff": "Affiliate link: we may earn a commission at no extra cost to you.",
           "deals": "Watch deals", "guides": "Guides", "pick": "Kabuzio Pick", "compare": "Compare"},
    "es": {"all": "← Todos los relojes", "cta": "Ver oferta en AliExpress", "bp": "Protección al comprador de AliExpress", "ship": "Envío a todo el mundo",
           "picked": "Los más vendidos, elegidos a mano", "sold": "{n}+ vendidos en AliExpress", "like": "También te puede gustar",
           "desc": "{what} por {price} en AliExpress{sold}. Elegido por Kabuzio. Protección al comprador y envío a todo el mundo.",
           "watch": "reloj", "soldshort": ", {n}+ vendidos", "more": "Más relojes cada día en nuestro",
           "social": "Telegram y redes", "aff": "Enlace de afiliado: podemos ganar una comisión sin coste extra para ti.",
           "deals": "Relojes", "guides": "Guías", "pick": "Selección Kabuzio", "compare": "Comparar"},
    "fr": {"all": "← Toutes les montres", "cta": "Voir l'offre sur AliExpress", "bp": "Protection acheteur AliExpress", "ship": "Livraison dans le monde entier",
           "picked": "Meilleures ventes choisies à la main", "sold": "{n}+ vendues sur AliExpress", "like": "Vous aimerez aussi",
           "desc": "{what} à {price} sur AliExpress{sold}. Sélection Kabuzio. Protection acheteur et livraison dans le monde entier.",
           "watch": "montre", "soldshort": ", {n}+ vendues", "more": "De nouvelles montres chaque jour sur notre",
           "social": "Telegram et réseaux", "aff": "Lien affilié : nous pouvons toucher une commission sans frais pour vous.",
           "deals": "Montres", "guides": "Guides", "pick": "Sélection Kabuzio", "compare": "Comparer"},
    "de": {"all": "← Alle Uhren", "cta": "Angebot auf AliExpress ansehen", "bp": "AliExpress Käuferschutz", "ship": "Weltweiter Versand",
           "picked": "Handverlesene Bestseller", "sold": "{n}+ auf AliExpress verkauft", "like": "Das könnte dir auch gefallen",
           "desc": "{what} für {price} auf AliExpress{sold}. Von Kabuzio ausgewählt. Käuferschutz und weltweiter Versand.",
           "watch": "Uhr", "soldshort": ", {n}+ verkauft", "more": "Jeden Tag neue Uhren auf unserem",
           "social": "Telegram und Social Media", "aff": "Affiliate-Link: Wir erhalten ggf. eine Provision, für dich ohne Mehrkosten.",
           "deals": "Uhren", "guides": "Ratgeber", "pick": "Kabuzio Auswahl", "compare": "Vergleich"},
    "pt": {"all": "← Todos os relógios", "cta": "Ver oferta no AliExpress", "bp": "Proteção ao comprador AliExpress", "ship": "Envio para todo o mundo",
           "picked": "Mais vendidos escolhidos a dedo", "sold": "{n}+ vendidos no AliExpress", "like": "Você também pode gostar",
           "desc": "{what} por {price} no AliExpress{sold}. Escolhido pela Kabuzio. Proteção ao comprador e envio para todo o mundo.",
           "watch": "relógio", "soldshort": ", {n}+ vendidos", "more": "Novos relógios todos os dias no nosso",
           "social": "Telegram e redes", "aff": "Link de afiliado: podemos ganhar uma comissão sem custo extra para você.",
           "deals": "Relógios", "guides": "Guias", "pick": "Seleção Kabuzio", "compare": "Comparar"},
    "it": {"all": "← Tutti gli orologi", "cta": "Vedi l'offerta su AliExpress", "bp": "Protezione acquirente AliExpress", "ship": "Spedizione in tutto il mondo",
           "picked": "I più venduti scelti a mano", "sold": "{n}+ venduti su AliExpress", "like": "Potrebbe piacerti anche",
           "desc": "{what} a {price} su AliExpress{sold}. Scelto da Kabuzio. Protezione acquirente e spedizione in tutto il mondo.",
           "watch": "orologio", "soldshort": ", {n}+ venduti", "more": "Nuovi orologi ogni giorno sul nostro",
           "social": "Telegram e social", "aff": "Link di affiliazione: potremmo ricevere una commissione senza costi per te.",
           "deals": "Orologi", "guides": "Guide", "pick": "Selezione Kabuzio", "compare": "Confronta"},
}

# watch kinds and features as bot/textos.py and bot/paginas.py write them
WORDS = {
    "es": {"Chronograph": "Cronógrafo", "Sport": "Deportivo", "Tourbillon": "Tourbillon", "Skeleton": "Esqueleto", "Automatic": "Automático",
           "Quartz": "Cuarzo", "Sapphire crystal": "Cristal de zafiro", "316L stainless steel": "Acero inoxidable 316L", "Titanium case": "Caja de titanio",
           "Ceramic bezel": "Bisel cerámico", "Bronze case": "Caja de bronce", "Automatic movement": "Movimiento automático", "Meteorite dial": "Esfera de meteorito",
           "Carbon fiber": "Fibra de carbono", "Luminous dial": "Esfera luminosa", "Stainless steel case": "Caja de acero inoxidable", "water resistant": "resistente al agua",
           "automatic movement": "movimiento automático", "movement": "movimiento"},
    "fr": {"Chronograph": "Chronographe", "Sport": "Sport", "Tourbillon": "Tourbillon", "Skeleton": "Squelette", "Automatic": "Automatique",
           "Quartz": "Quartz", "Sapphire crystal": "Verre saphir", "316L stainless steel": "Acier inoxydable 316L", "Titanium case": "Boîtier en titane",
           "Ceramic bezel": "Lunette céramique", "Bronze case": "Boîtier en bronze", "Automatic movement": "Mouvement automatique", "Meteorite dial": "Cadran météorite",
           "Carbon fiber": "Fibre de carbone", "Luminous dial": "Cadran luminescent", "Stainless steel case": "Boîtier en acier inoxydable", "water resistant": "étanche",
           "automatic movement": "mouvement automatique", "movement": "mouvement"},
    "de": {"Chronograph": "Chronograph", "Sport": "Sport", "Tourbillon": "Tourbillon", "Skeleton": "Skelett", "Automatic": "Automatik",
           "Quartz": "Quarz", "Sapphire crystal": "Saphirglas", "316L stainless steel": "Edelstahl 316L", "Titanium case": "Titangehäuse",
           "Ceramic bezel": "Keramiklünette", "Bronze case": "Bronzegehäuse", "Automatic movement": "Automatikwerk", "Meteorite dial": "Meteoritenzifferblatt",
           "Carbon fiber": "Carbon", "Luminous dial": "Leuchtzifferblatt", "Stainless steel case": "Edelstahlgehäuse", "water resistant": "wasserdicht",
           "automatic movement": "Automatikwerk", "movement": "Werk"},
    "pt": {"Chronograph": "Cronógrafo", "Sport": "Esportivo", "Tourbillon": "Tourbillon", "Skeleton": "Esqueleto", "Automatic": "Automático",
           "Quartz": "Quartzo", "Sapphire crystal": "Cristal de safira", "316L stainless steel": "Aço inoxidável 316L", "Titanium case": "Caixa de titânio",
           "Ceramic bezel": "Bisel de cerâmica", "Bronze case": "Caixa de bronze", "Automatic movement": "Movimento automático", "Meteorite dial": "Mostrador de meteorito",
           "Carbon fiber": "Fibra de carbono", "Luminous dial": "Mostrador luminoso", "Stainless steel case": "Caixa de aço inoxidável", "water resistant": "resistente à água",
           "automatic movement": "movimento automático", "movement": "movimento"},
    "it": {"Chronograph": "Cronografo", "Sport": "Sportivo", "Tourbillon": "Tourbillon", "Skeleton": "Scheletrato", "Automatic": "Automatico",
           "Quartz": "Quarzo", "Sapphire crystal": "Vetro zaffiro", "316L stainless steel": "Acciaio inox 316L", "Titanium case": "Cassa in titanio",
           "Ceramic bezel": "Lunetta in ceramica", "Bronze case": "Cassa in bronzo", "Automatic movement": "Movimento automatico", "Meteorite dial": "Quadrante meteorite",
           "Carbon fiber": "Fibra di carbonio", "Luminous dial": "Quadrante luminoso", "Stainless steel case": "Cassa in acciaio inox", "water resistant": "impermeabile",
           "automatic movement": "movimento automatico", "movement": "movimento"},
}


def w(lang, s):
    """Translate a kind or feature («100m water resistant», «NH35 automatic movement» too)."""
    if lang == "en" or not s:
        return s
    d = WORDS[lang]
    if s in d:
        return d[s]
    for k in ("water resistant", "automatic movement", "movement"):
        if s.endswith(" " + k):
            return s[: -len(k)] + d[k]
    return s


def prefix(lang):
    """Path of a language inside the site: '' for English, 'es/' for Spanish..."""
    return "" if lang == "en" else lang + "/"
