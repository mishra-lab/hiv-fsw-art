import os,sys,re
# setup
igs = [
  '(?<!\\\\)%.*',
  '\\\\(par|item)\\s',
  # '\\s*?\\\\cite\{.*?\}',
  # '\\\\input\{.*?\}',
  '\\\\label\{.*?\}',
  '\\\\(begin|end)\{(enumerate|itemize)\}',
]
envs = [
  re.compile('\\s*?\\\\begin\{'+env+'\}(.*?)\\\\end\{'+env+'\}',re.DOTALL)
  for env in ['table','figure','equation','alignat']
]
reps = [
  ('~', ' '),
  ('(``|\'\')', '"'),
  ('\\$(.*?)\\$', '\\1'),
  ('\\\\times', 'x'),
  ('\\\\emph\{(.*?)\}', '\\1'),
  ('\\\\text..\{(.*?)\}', '\\1'),
  ('\\\\(?:sub)*section\{(.*?)\}', '\n\\1\n'),
  ('\\\\paragraph\{(.*?)\}', '\n\\1\n'),
  ('\\\\ref\{(.*?)\}', '\\1'),
  ('\\\\cite\{(.*?)\}', '[\\1]'),
  ('\\\\href\{.*?\}\{(.*?)\}', '\\1'),
]
# main
def wc(label,files,clean=True):
  # load
  text = ''
  for file in files:
    with open(file+'.tex','r') as f:
      text += '\n\n<<<'+file.upper()+'>>>\n\n'+f.read()
  # clean
  for k,v in reps:   text = re.sub(k,v,text)
  for i in igs+envs: text = re.sub(i,'',text)
  for n in range(9): text = text.replace('\\s*\n','\n').replace('\n\n\n','\n\n')
  # output
  with open('text.tmp','w') as f:
    f.write(text)
  os.system('echo -n \ '+label+':\ && wc -w text.tmp | cut -d " " -f1')
  if clean:
    os.system('rm text.tmp')

wc(' abs',[sys.argv[1]])
wc('body',sys.argv[2:])
