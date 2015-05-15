import scipy as sp

if __package__ is None:
    __package__ = 'modules'

from .reads import *

def make_introns_feasible(introns, genes, CFG):
# introns = make_introns_feasible(introns, genes, CFG)

    tmp1 = sp.array([x.shape[0] for x in introns[:, 0]])
    tmp2 = sp.array([x.shape[0] for x in introns[:, 1]])
    
    unfeas = sp.where((tmp1 > 200) | (tmp2 > 200))[0]
    print >> CFG['fd_log'], 'found %i unfeasible genes' % unfeas.shape[0]

    while unfeas.shape[0] > 0:
        ### make filter more stringent
        CFG['read_filter']['exon_len'] = min(36, CFG['read_filter']['exon_len'] + 4)
        CFG['read_filter']['mincount'] = 2 * CFG['read_filter']['mincount']
        CFG['read_filter']['mismatch'] = max(CFG['read_filter']['mismatch'] - 1, 0)

        ### get new intron counts
        tmp_introns = get_intron_list(genes[unfeas], CFG)
        introns[unfeas, :] = tmp_introns

        ### stil unfeasible?
        tmp1 = sp.array([x.shape[0] for x in introns[:, 0]])
        tmp2 = sp.array([x.shape[0] for x in introns[:, 1]])

        still_unfeas = sp.where((tmp1 > 200) | (tmp2 > 200))[0]
        idx = sp.where(~sp.in1d(unfeas, still_unfeas))[0]

        for i in unfeas[idx]:
            print >> CFG['fd_log'], '[feasibility] set criteria for gene %s to: min_ex %i, min_conf %i, max_mism %i' % (genes[i].name, CFG['read_filter']['exon_len'], CFG['read_filter']['mincount'], CFG['read_filter']['mismatch'])
        unfeas = still_unfeas;

    return introns

### determine count output file
def get_filename(which, CFG):
    """This function returns a filename generated from the current configuration"""

    ### init any tags
    prune_tag = ''
    if CFG['do_prune']:
        prune_tag = '_pruned'

    ### iterate over return file types    
    if which in ['fn_count_in', 'fn_count_out']:
        if not 'spladder_infile' in CFG:
            if CFG['validate_splicegraphs']:
                fname = os.path.join(CFG['out_dirname'], 'spladder', 'genes_graph_conf%i.%s%s.validated.pickle' % (CFG['confidence_level'], CFG['merge_strategy'], prune_tag))
            else:
                fname = os.path.join(CFG['out_dirname'], 'spladder', 'genes_graph_conf%i.%s%s.pickle' % (CFG['confidence_level'], CFG['merge_strategy'], prune_tag))
        else:
            fname = CFG['spladder_infile']
        
        if which == 'fn_count_in':
            return fname
        elif which == 'fn_count_out':
            return fname.replace('.pickle', '') + '.count.pickle'
    elif which == 'fn_out_merge':
        if CFG['merge_strategy'] == 'merge_graphs':
            return os.path.join(CFG['out_dirname'], 'spladder', 'genes_graph_conf%i.%s%s.pickle' % (CFG['confidence_level'], CFG['merge_strategy'], prune_tag))
        else:
            return ''
