% !TeX root = ./main.tex
%% CCJNL.cls 2020/08/22 version V1.0  by MaWei
%% CCJNL.cls 2022/11/22 version V2.0  by MaWei

\ProvidesClass{ccjnl}[2020/08/22 V1.0 by MaWei]
\NeedsTeXFormat{LaTeX2e}
\LoadClass[twoside,twocolumn]{article}

\RequirePackage{etoolbox}
\RequirePackage{geometry}
\RequirePackage{graphicx}
\RequirePackage{epstopdf}
\RequirePackage{booktabs}
\RequirePackage{setspace}
\RequirePackage{algorithm,algorithmic}
\RequirePackage{titlesec}
\RequirePackage{xcolor}
\RequirePackage{tikz}
\RequirePackage{anyfontsize}
\RequirePackage{wrapfig}
\RequirePackage[labelfont={bf,scriptsize},textfont={scriptsize,it}]{subfig}
\RequirePackage{enumitem}
\RequirePackage{endnotes}
\RequirePackage{listings}
\RequirePackage{amsmath,amssymb,amsthm,siunitx,makecell,cuted}
\allowdisplaybreaks[4]
\setlength{\stripsep}{0pt plus 3pt minus 2pt}
\RequirePackage{caption}
\RequirePackage[multiple,bottom]{footmisc}
\RequirePackage[colorlinks,allcolors=blue,urlcolor=black]{hyperref}
\RequirePackage[nameinlink]{cleveref}
\RequirePackage[numbers,compress]{natbib}
\graphicspath{{figures/}}
\geometry{a4paper,left=1.8cm,right=1.8cm,marginparsep=2pt,top=2.5cm,bottom=2.5cm,includeheadfoot,headsep=10pt,footskip=0.4cm}
\setlength{\columnsep}{0.7cm}


% endnotes
\let\footnote\undefined

% skip before-after equation
\setlength{\abovedisplayskip}{16pt plus 1pt minus 1pt}
\setlength{\belowdisplayskip}{16pt plus 1pt minus 1pt}

% contant
\def\journal{China Communications}
\def\corrinfo{The corresponding author}
\def\emailname{email}
\def\receivedname{Received}
\def\revisedname{Revised}
\def\editorname{Editor}
\def\abstractname{Abstract}
\def\keywordsname{Keywords}
\def\appendixname{APPENDIX}
\def\referencesname{References}
\def\biographiesname{Biographies}
\def\inputname{Input}
\def\outputname{Output}

\ExplSyntaxOn
\clist_set:Nn \l__ignore_prep_clist
  {
    in, to, the, for, on, this, into, onto, at, by, within, about, and, or, than, until, of
  }
\clist_set:Nn \l__theorem_style_label_clist
  {
    theorem, definition, lemma, proposition, corollary, example, exercise, remark, case
  }
\ExplSyntaxOff

\newcommand{\receiveddate}[1]{\def\CCJNLreceiveddate{#1}}
\newcommand{\reviseddate}[1]{\def\CCJNLreviseddate{#1}}
\newcommand{\Editor}[1]{\def\CCJNLEditor{#1}}

% font type
\renewcommand{\rmdefault}{ptm}
\renewcommand{\sfdefault}{phv}
\renewcommand{\ttdefault}{ppl}

% font size
\def\yihao{\fontsize{25pt}{30pt}\selectfont}\let\Huge\yihao
% \def\xiaoyi{\fontsize{24pt}{32pt}\selectfont}
\def\erhao{\fontsize{20pt}{26pt}\selectfont}\let\huge\erhao
\def\xiaoer{\fontsize{17pt}{26pt}\selectfont}\let\LARGE\xiaoer
% \def\sanhao{\fontsize{16pt}{21pt}\selectfont}
\def\xiaosan{\fontsize{14pt}{18pt}\selectfont}\let\Large\xiaosan
% \def\sihao{\fontsize{14pt}{18pt}\selectfont}
\def\xiaosi{\fontsize{12pt}{15pt}\selectfont}\let\large\xiaosi
\def\wuhao{\fontsize{11pt}{14pt}\selectfont}\let\normalsize\wuhao
\def\xiaowu{\fontsize{10pt}{12pt}\selectfont}\let\small\xiaowu
\def\liuhao{\fontsize{9pt}{11pt}\selectfont}\let\footnotesize\liuhao
\def\xiaoliu{\fontsize{8pt}{10pt}\selectfont}\let\scriptsize\xiaoliu
\def\qihao{\fontsize{6pt}{8pt}\selectfont}\let\qihao\tiny
\def\endfont{\fontsize{9pt}{11.6pt}\selectfont}

% page layout
\newcommand{\headruleheight}{0.283pt}
\newlength\headrulewidth
\setlength\headrulewidth{\textwidth}
\def\headrule{%
  \rule{\headrulewidth}{\headruleheight}%
}
\def\footrule{%
    \rule[0pt]{\headrulewidth}{\headruleheight}\\
    \rule[10pt]{\headrulewidth}{\headruleheight}%
}

\def\@oddhead{\leavevmode\hbox to \textwidth{\hskip-0.1pt%
  \headrule\hfill \kern\z@}}%
\let\@evenhead\@oddhead

\def\@oddfoot{%
    {\hskip-1.6pt\parbox[t]{\headrulewidth}{\footrule\vskip-10pt%
    \hbox to \headrulewidth{{\footnotesize\journal}  \hfill  {\sffamily\small\thepage}}}%
}}
\def\@evenfoot{%
  \hskip-1.6pt\parbox[t]{\headrulewidth}{\footrule\vskip-10pt%
    \hbox to \headrulewidth{{\small\sffamily\thepage} \hfill {\footnotesize\journal}}}%
}

% maketitle
\newlength\boxwidth
\setlength\boxwidth{\textwidth}
\addtolength\boxwidth{-6pt}
\def\titlerule{%
    {{\rule{6cm}{1pt}}}%
}

\def\inst#1{\textsuperscript{\fontsize{6.1pt}{8pt}\selectfont #1}}
\newcommand\corinfo[1]{\gdef\CCJNLcorinfo{\textsuperscript{\fontsize{5.2pt}{7pt}\selectfont *~}\fontsize{9pt}{12.8pt}\selectfont\corrinfo, \emailname: #1}}


\def\CCJNLaddress{}
\def\CCJNLcorinfo{}
\def\addsep{\par\vskip6pt}
\def\address{\@ifnextchar[{\@address}{}}
\long\def\@address[#1]#2{\g@addto@macro\CCJNLaddress{%
  \textsuperscript{\fontsize{5.2pt}{7pt}\selectfont #1~}{\fontsize{9pt}{12.8pt}\selectfont #2\\}}\par}

\def\maketitle{
  \twocolumn[
  \begin{@twocolumnfalse}
    {\tikz\fill[fill=white] (0,0) rectangle (\textwidth,0.3);
    \vskip-11pt
    {\parbox[t]{\boxwidth}{\vfill\hskip-3pt\parbox{\boxwidth}{\raggedright\large\sffamily\scshape\bfseries\journal}\vfill}}\vskip1cm
    \raggedright{\LARGE\sffamily\bfseries\@title\par}\vskip12pt
    \titlerule\\
    {\bfseries\fontsize{10.5pt}{12pt}\selectfont\@author}\vskip12pt
    \scriptsize\CCJNLaddress\CCJNLcorinfo
    \vskip1cm}
  \end{@twocolumnfalse}
  ]
  {\let\thefootnote\relax\footnotetext{\parbox[t]{0.45\textwidth}{
      {{\textbf{\receivedname:~}\CCJNLreceiveddate}}\\
      {{\textbf{\revisedname:~}\CCJNLreviseddate}}\\
      {{\textbf{\editorname:~}\CCJNLEditor}}\\
    }}}
}

%keywords
\newcommand{\keywords}[1]{\def\CCJNLkeywords{#1}}
% abstract
\renewenvironment{abstract}{\noindent\textbf{\abstractname:~}}{\\\textbf{\keywordsname:~}\CCJNLkeywords\par}

% section title
\renewcommand{\thesection}{\Roman{section}}
\renewcommand{\thesubsection}{\arabic{section}.\arabic{subsection}}
\renewcommand{\thesubsubsection}{\thesubsection.\arabic{subsubsection}}

\ExplSyntaxOn
\seq_set_from_clist:NN \l__ignore_prep_seq \l__ignore_prep_clist
\NewExpandableDocumentCommand \uppercap { m } { \text_uppercase:n { #1 } }
\NewExpandableDocumentCommand \firstcap { m }
  {
    \seq_set_split:Nnn \l_tmpa_seq { ~ } { #1 }
    \seq_clear:N \l_tmpb_seq
    \seq_map_inline:Nn \l_tmpa_seq
      {
        \seq_put_right:Nn \l_tmpb_seq
          {
            \seq_if_in:NnTF \l__ignore_prep_seq { ##1 }
              { ##1 }
              { \text_uppercase:n ##1 }
          }
      }
    \seq_use:Nn \l_tmpb_seq { ~ }
  }
\ExplSyntaxOff

\titleformat{\section}{\large\bfseries\boldmath}{\thesection.}{0.5em}{\uppercap}
\titleformat{\subsection}{\large\bfseries\boldmath}{\thesubsection}{0.5em}{\firstcap}
\titleformat{\subsubsection}{}{\thesubsubsection}{0.5em}{\firstcap}
\titleformat{\paragraph}[runin]{\bfseries\boldmath\filright}{}{0.5em}{\firstcap}


\captionsetup[figure]{textfont={it,small},labelfont={bf},labelsep=period,name=Figure}
\captionsetup[table]{textfont={it,footnotesize},labelfont={footnotesize,bf},labelsep=period}
\captionsetup[algorithm]{textfont={it,footnotesize},labelfont=bf,labelsep=period}

\AtBeginEnvironment{tabular}{\scriptsize}

\newenvironment{breakablealgorithm}
  {% \begin{breakablealgorithm}
   \begin{center}
     \refstepcounter{algorithm}% New algorithm
     \hrule height.8pt depth0pt \kern2pt% \@fs@pre for \@fs@ruled
     \renewcommand{\caption}[2][\relax]{% Make a new \caption
       {\raggedright\small\textbf{\fname@algorithm~\thealgorithm.} \textit{##2}\par}%
       \ifx\relax##1\relax % #1 is \relax
         \addcontentsline{loa}{algorithm}{\protect\numberline{\thealgorithm}##2}%
       \else % #1 is not \relax
         \addcontentsline{loa}{algorithm}{\protect\numberline{\thealgorithm}##1}%
       \fi
       \kern2pt\hrule\kern2pt
     }
  }{% \end{breakablealgorithm}
     \kern2pt\hrule\relax% \@fs@post for \@fs@ruled
   \end{center}
  }

\renewcommand{\bibsep}{0pt}

\renewcommand\appendix{\par
  \setcounter{section}{0}%
  \setcounter{subsection}{0}%
  \gdef\thesection{\Alph{subsection}}
  \gdef\thesubsection{\Alph{subsection}}
  \gdef\theequation{\thesubsection.\arabic{equation}}
  \numberwithin{equation}{subsection}
%   \section*{\appendixname}
  \protect\vskip12pt\section*{\appendixname}\vskip12pt
}

% footnote
\setlength{\footnotemargin}{0.5em}
\setlength{\footnotesep}{0pt}
\def\footnoterule{
  \noindent{\rule{4cm}{0.283pt}}\vskip5pt
}

% Biography
\newdimen\CCJNLdimenA
\newenvironment{CCJNLbiography}[2]{
\begin{figure}[!h]
  \vskip-26pt
    \def\CCJNLtempbiographybox{\mbox{\begin{minipage}[b][1in][c]{1.25in}\centering
    \includegraphics[width=1in,height=1.25in,clip,keepaspectratio]{#1}
    \end{minipage}}}
    \let\CCJNLBiopar=\par
    \edef\par{\hfil\break\indent}
    \par
    \setlength\hangindent{1.2in}
    \setlength\hangafter{-10}
    \settoheight{\CCJNLdimenA}{\mbox{T}}
    \makebox[0pt][l]{\hspace{-1.5in}\raisebox{0.6\CCJNLdimenA}[0pt][0pt]{
    \raisebox{-1.25in}[0pt][0pt]{\CCJNLtempbiographybox}}}\\
    \endfont\noindent\textbf{\itshape #2} \ }
    {\relax\let\par=\CCJNLBiopar\par%
    \vskip12pt
\end{figure}
  }


\renewcommand\enoteformat{\rightskip=0pt \leftskip=0pt \parindent=0em
\leavevmode\makeenmark\normalsize}

\renewcommand{\bibsection}{{\subsection*{\referencesname}}}
\newcommand{\biographies}{{\subsection*{\biographiesname}}}

\lstset{frame=single,frameround=tttt,breaklines=true,basicstyle=\scriptsize}

\setlist{itemsep=0pt, topsep=0pt}

\ExplSyntaxOn
\cs_new_protected_nopar:Npn \__ccjnl_new_theorem:n #1
  {
    \newtheorem { #1 } { \text_titlecase:n { #1 } }
    \newtheorem* { #1* } { \text_titlecase:n { #1 } }
  }
\clist_map_function:NN \l__theorem_style_label_clist \__ccjnl_new_theorem:n
\ExplSyntaxOff

%colorbox
% \RequirePackage{tcolorbox}
% \tcbuselibrary{theorems,skins,breakable}
\renewcommand{\qedsymbol}{}
% \tcolorboxenvironment{proof}{enhanced jigsaw,colframe=cyan,interior hidden,breakable,before skip=10pt,after skip=10pt}

\renewcommand{\algorithmicrequire}{ \textbf{\inputname:}} %Use Input in the format of Algorithm
\renewcommand{\algorithmicensure}{ \textbf{\outputname:}} %UseOutput in the format of Algorithm
