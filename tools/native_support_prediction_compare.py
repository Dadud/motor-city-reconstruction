"""Compare the native support predictor with authored projection observations."""
import json
import subprocess
from tools.support_prediction_oracle import cases, encode, predict_support, projection


def verify(runner):
    corpus=list(cases())
    lines=[]
    expected=[]
    for state,observation in corpus:
        mask,rewrite=observation
        result=predict_support(state,lambda q:projection(q,observation))
        expected.append((encode(result.state),result.queries))
        lines.append(f'{encode(state).hex()} {mask} {int(rewrite)}')
    proc=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=60)
    rows=proc.stdout.splitlines()
    if len(rows)!=len(corpus):raise AssertionError(('native output count',len(rows),len(corpus)))
    for index,(row,(image,queries)) in enumerate(zip(rows,expected)):
        tokens=row.split()
        actual=bytes.fromhex(tokens.pop(0))
        if actual!=image:
            offset=next(i for i,(a,b) in enumerate(zip(actual,image)) if a!=b)
            raise AssertionError(('owner bytes',index,hex(offset),actual[offset:offset+8],image[offset:offset+8]))
        values=list(map(float,tokens))
        if len(values)!=len(queries)*7:raise AssertionError(('query count',index,len(values)))
        for slot,q in enumerate(queries):
            row_values=values[slot*7:(slot+1)*7]
            if int(row_values[0])!=q.context or tuple(row_values[1:4])!=q.point or tuple(row_values[4:7])!=q.previous_world:
                raise AssertionError(('ordered query',index,slot,row_values,q))
    return {'cases':len(corpus),'owner_bytes':'exact','queries':'exact ordered context, points, and previous positions',
            'scope':'native support-prediction arithmetic with authored terrain projections; original projection remains external'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
