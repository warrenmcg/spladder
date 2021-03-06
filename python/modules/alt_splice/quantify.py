import scipy as sp
import scipy.io as scio
import cPickle
import h5py
import sys
import os

if __package__ is None:
    __package__ = 'modules.alt_splice'

from ..utils import *
from ..helpers import *

def quantify_mult_exon_skip(event, gene, counts_segments, counts_edges, CFG):

    cov = sp.zeros((2, ), dtype='float')

    sg = gene.splicegraph
    segs = gene.segmentgraph

    if CFG['is_matlab']:
        seg_lens = segs[0, 0][1, :] - segs[0, 0][0, :]
        seg_shape = segs[0, 2].shape[0]
        order = 'F'
        offset = 1

        ### find exons corresponding to event
        idx_exon_pre  = sp.where((sg[0, 0][0, :] == event.exon_pre[0]) & (sg[0, 0][1, :] == event.exon_pre[1]))[0]
        idx_exon_aft  = sp.where((sg[0, 0][0, :] == event.exon_aft[0]) & (sg[0, 0][1, :] == event.exon_aft[1]))[0]
        seg_exons = []
        for i in range(0, event.exons.shape[1], 2):
            tmp = sp.where((sg[0, 0][0, :] == event.exons[i]) & (sg[0, 0][1, :] == event.exons[i + 1]))[0]
            seg_exons.append(sp.where(segs[0, 1][tmp, :])[1])
        
        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs[0, 1][idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs[0, 1][idx_exon_aft, :])[1])
    else:
        seg_lens = segs.segments[1, :] - segs.segments[0, :]
        seg_shape = segs.seg_edges.shape[0]
        order = 'C'
        offset = 0

        ### find exons corresponding to event
        idx_exon_pre  = sp.where((sg.vertices[0, :] == event.exons2[0, 0]) & (sg.vertices[1, :] == event.exons2[0, 1]))[0]
        idx_exon_aft  = sp.where((sg.vertices[0, :] == event.exons2[-1, 0]) & (sg.vertices[1, :] == event.exons2[-1, 1]))[0]
        seg_exons = []
        for i in range(1, event.exons2.shape[0] - 1):
            tmp = sp.where((sg.vertices[0, :] == event.exons2[i, 0]) & (sg.vertices[1, :] == event.exons2[i, 1]))[0]
            seg_exons.append(sp.where(segs.seg_match[tmp, :])[1])
        
        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs.seg_match[idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs.seg_match[idx_exon_aft, :])[1])

    seg_exons_u = sp.sort(sp.unique([x for sublist in seg_exons for x in sublist]))

    ### inner exons_cov
    cov[0] = sp.sum(counts_segments[seg_exons_u] * seg_lens[seg_exons_u]) / sp.sum(seg_lens[seg_exons_u])

    ### check intron confirmation as sum of valid intron scores
    ### intron score is the number of reads confirming this intron
    # exon_pre_exon_conf
    idx1 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exons[0][0]], seg_shape, order=order) + offset)[0]
    if len(idx1.shape) > 0 and idx1.shape[0] > 0:
        cov[0] += counts_edges[idx1[0], 1]
    # exon_exon_aft_conf
    idx2 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exons[-1][-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    if len(idx2.shape) > 0 and idx2.shape[0] > 0:
        cov[0] += counts_edges[idx2[0], 1]
    # exon_pre_exon_aft_conf
    idx3 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    if len(idx3.shape) > 0 and idx3.shape[0] > 0:
        cov[1] = counts_edges[idx3[0], 1]
    for i in range(len(seg_exons) - 1):
        # sum_inner_exon_conf
        idx4 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exons[i][-1], seg_exons[i+1][0]], seg_shape, order=order) + offset)[0]
        if len(idx4.shape) > 0 and idx4.shape[0] > 0:
            cov[0] += counts_edges[idx4[0], 1]

    return cov


def quantify_intron_retention(event, gene, counts_segments, counts_edges, counts_seg_pos, CFG):

    cov = sp.zeros((2, ), dtype='float')
    sg = gene.splicegraph
    segs = gene.segmentgraph

    if CFG['is_matlab']:
        seg_lens = segs[0, 0][1, :] - segs[0, 0][0, :]
        seg_shape = segs[0, 2].shape
        order = 'F'
        offset = 1

        ### find exons corresponding to event
        idx_exon1  = sp.where((sg[0, 0][0, :] == event.exon1[0]) & (sg[0, 0][1, :] == event.exon1[1]))[0]
        idx_exon2  = sp.where((sg[0, 0][0, :] == event.exon2[0]) & (sg[0, 0][1, :] == event.exon2[1]))[0]

        ### find segments corresponding to exons
        seg_exon1 = sp.sort(sp.where(segs[0, 1][idx_exon1, :])[1])
        seg_exon2 = sp.sort(sp.where(segs[0, 1][idx_exon2, :])[1])
    else:
        seg_lens = segs.segments[1, :] - segs.segments[0, :]
        seg_shape = segs.seg_edges.shape
        order = 'C'
        offset = 0

        ### find exons corresponding to event
        idx_exon1  = sp.where((sg.vertices[0, :] == event.exons1[0, 0]) & (sg.vertices[1, :] == event.exons1[0, 1]))[0]
        idx_exon2  = sp.where((sg.vertices[0, :] == event.exons1[1, 0]) & (sg.vertices[1, :] == event.exons1[1, 1]))[0]

        ### find segments corresponding to exons
        seg_exon1 = sp.sort(sp.where(segs.seg_match[idx_exon1, :])[1])
        seg_exon2 = sp.sort(sp.where(segs.seg_match[idx_exon2, :])[1])
    seg_all = sp.arange(seg_exon1[0], seg_exon2[-1])

    seg_intron = sp.setdiff1d(seg_all, seg_exon1)
    seg_intron = sp.setdiff1d(seg_intron, seg_exon2)
    assert(seg_intron.shape[0] > 0)

    ### compute exon coverages as mean of position wise coverage
    # intron_cov
    cov[0] = sp.sum(counts_segments[seg_intron] * seg_lens[seg_intron]) / sp.sum(seg_lens[seg_intron])

    ### check intron confirmation as sum of valid intron scores
    ### intron score is the number of reads confirming this intron
    # intron conf
    idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon1[-1], seg_exon2[0]], seg_shape, order=order) + offset)[0]
    cov[1] = counts_edges[idx, 1]

    return cov


def quantify_exon_skip(event, gene, counts_segments, counts_edges, CFG):

    cov = sp.zeros((2, ), dtype='float')
    sg = gene.splicegraph
    segs = gene.segmentgraph

    if CFG['is_matlab']:
        seg_lens = segs[0, 0][1, :] - segs[0, 0][0, :]
        seg_shape = segs[0, 2].shape
        order = 'F'
        offset = 1

        ### find exons corresponding to event
        idx_exon_pre = sp.where((sg[0, 0][0, :] == event.exon_pre[0]) & (sg[0, 0][1, :] == event.exon_pre[1]))[0]
        idx_exon = sp.where((sg[0, 0][0, :] == event.exon[0]) & (sg[0, 0][1, :] == event.exon[1]))[0]
        idx_exon_aft = sp.where((sg[0, 0][0, :] == event.exon_aft[0]) & (sg[0, 0][1, :] == event.exon_aft[1]))[0]

        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs[0, 1][idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs[0, 1][idx_exon_aft, :])[1])
        seg_exon = sp.sort(sp.where(segs[0, 1][idx_exon, :])[1])
    else:
        seg_lens = segs.segments[1, :] - segs.segments[0, :]
        seg_shape = segs.seg_edges.shape
        order = 'C'
        offset = 0

        ### find exons corresponding to event
        idx_exon_pre = sp.where((sg.vertices[0, :] == event.exons2[0, 0]) & (sg.vertices[1, :] == event.exons2[0, 1]))[0]
        idx_exon = sp.where((sg.vertices[0, :] == event.exons2[1, 0]) & (sg.vertices[1, :] == event.exons2[1, 1]))[0]
        idx_exon_aft = sp.where((sg.vertices[0, :] == event.exons2[2, 0]) & (sg.vertices[1, :] == event.exons2[2, 1]))[0]

        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs.seg_match[idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs.seg_match[idx_exon_aft, :])[1])
        seg_exon = sp.sort(sp.where(segs.seg_match[idx_exon, :])[1])

    # get inner exon cov
    cov[0] = sp.sum(counts_segments[seg_exon] * seg_lens[seg_exon]) /sp.sum(seg_lens[seg_exon])

    ### check intron confirmation as sum of valid intron scores
    ### intron score is the number of reads confirming this intron
    # exon_pre_exon_conf
    idx1 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exon[0]], seg_shape, order=order) + offset)[0]
    cov[0] += counts_edges[idx1, 1]
    # exon_exon_aft_conf
    idx2 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon[-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    cov[0] += counts_edges[idx2, 1]
    # exon_pre_exon_aft_conf
    idx3 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    cov[1] = counts_edges[idx3, 1]

    return cov


def quantify_alt_prime(event, gene, counts_segments, counts_edges, CFG):

    cov = sp.zeros((2, ), dtype='float')

    sg = gene.splicegraph
    segs = gene.segmentgraph
    if CFG['is_matlab']:
        seg_lens = segs[0, 0][1, :] - segs[0, 0][0, :]
        seg_shape = segs[0, 2].shape[0]

        idx_exon_alt1 = sp.where((sg[0, 0][0, :] == event.exon_alt1[0]) & (sg[0, 0][1, :] == event.exon_alt1[1]))
        idx_exon_alt2 = sp.where((sg[0, 0][0, :] == event.exon_alt2[0]) & (sg[0, 0][1, :] == event.exon_alt2[1]))
        idx_exon_const = sp.where((sg[0, 0][0, :] == event.exon_const[0]) & (sg[0, 0][1, :] == event.exon_const[1]))
        if idx_exon_alt1.shape[0] == 0:
            segs_exon_alt1 = sp.where((segs[0, 0][0, :] >= event.exon_alt1[0]) & (segs[0, 0][1, :] >= event.exon_alt1[1]))
        else:
            segs_exon_alt1 = sp.where(segs[0, 1][idx_exon_alt1, :])[1]
        if idx_exon_alt2.shape[0] == 0:
            segs_exon_alt2 = sp.where((segs[0, 0][0, :] >= event.exon_alt2[0]) & (segs[0, 0][1, :] >= event.exon_alt2[1]))
        else:
            segs_exon_alt2 = sp.where(segs[0, 1][idx_exon_alt2, :])[1]
        if idx_exon_const.shape[0] == 0:
            segs_exon_const = sp.where((segs[0, 0][0, :] >= event.exon_const[0]) & (segs[0, 0][1, :] >= event.exon_const[1]))
        else:
            segs_exon_const = sp.where(segs[0, 1][idx_exon_const, :])[1]

        assert(segs_exon_alt1.shape[0] > 0)
        assert(segs_exon_alt2.shape[0] > 0)
        assert(segs_exon_const.shape[0] > 0)

        cov[1] += sp.sum(counts_segments[seg_diff] * seg_lens[seg_diff]) / sp.sum(seg_lens[seg_diff])

        ### check intron confirmations as sum of valid intron scores
        ### intron score is the number of reads confirming this intron
        if max(segs_exon_alt1[-1], segs_exon_alt2[-1]) < segs_exon_const[0]:
            # intron1_conf 
            idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon_alt1[0], segs_exon_const[-1]], seg_shape))[0] + 1
            assert(idx.shape[0] > 0)
            cov[0] += counts_edges[idx, 1]
            # intron2_conf 
            idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon_alt2[0], segs_exon_const[-1]], seg_shape))[0] + 1
            assert(idx.shape[0] > 0)
            cov[1] += counts_edges[idx, 1]
        elif min(segs_exon_alt1[0], segs_exon_alt2[0]) > segs_exon_const[-1]:
            # intron1_conf 
            idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon_const[0], segs_exon_alt1[-1]], seg_shape))[0] + 1
            assert(idx.shape[0] > 0)
            cov[0] += counts_edges[idx, 1]
            # intron2_conf 
            idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon_const[0], segs_exon_alt2[-1]], seg_shape))[0] + 1
            assert(idx.shape[0] > 0)
            cov[1] += counts_edges[idx, 1]
    else:
        seg_lens = segs.segments[1, :] - segs.segments[0, :]
        seg_shape = segs.seg_edges.shape[0]

        ### find exons corresponding to event
        idx_exon11 = sp.where((sg.vertices[0, :] == event.exons1[0, 0]) & (sg.vertices[1, :] == event.exons1[0, 1]))[0]
        if idx_exon11.shape[0] == 0:
            segs_exon11 = sp.where((segs.segments[0, :] >= event.exons1[0, 0]) & (segs.segments[1, :] <= event.exons1[0, 1]))[0]
        else:
            segs_exon11 = sp.where(segs.seg_match[idx_exon11, :])[1]
        idx_exon12 = sp.where((sg.vertices[0, :] == event.exons1[1, 0]) & (sg.vertices[1, :] == event.exons1[1, 1]))[0]
        if idx_exon12.shape[0] == 0:
            segs_exon12 = sp.where((segs.segments[0, :] >= event.exons1[1, 0]) & (segs.segments[1, :] <= event.exons1[1, 1]))[0]
        else:
            segs_exon12 = sp.where(segs.seg_match[idx_exon12, :])[1]
        idx_exon21 = sp.where((sg.vertices[0, :] == event.exons2[0, 0]) & (sg.vertices[1, :] == event.exons2[0, 1]))[0]
        if idx_exon21.shape[0] == 0:
            segs_exon21 = sp.where((segs.segments[0, :] >= event.exons2[0, 0]) & (segs.segments[1, :] <= event.exons2[0, 1]))[0]
        else:
            segs_exon21 = sp.where(segs.seg_match[idx_exon21, :])[1]
        idx_exon22 = sp.where((sg.vertices[0, :] == event.exons2[1, 0]) & (sg.vertices[1, :] == event.exons2[1, 1]))[0]
        if idx_exon22.shape[0] == 0:
            segs_exon22 = sp.where((segs.segments[0, :] >= event.exons2[1, 0]) & (segs.segments[1, :] <= event.exons2[1, 1]))[0]
        else:
            segs_exon22 = sp.where(segs.seg_match[idx_exon22, :] > 0)[1]

        assert(segs_exon11.shape[0] > 0)
        assert(segs_exon12.shape[0] > 0)
        assert(segs_exon21.shape[0] > 0)
        assert(segs_exon22.shape[0] > 0)

        if sp.all(segs_exon11 == segs_exon21):
            seg_diff = sp.setdiff1d(segs_exon12, segs_exon22)
            if seg_diff.shape[0] == 0:
                seg_diff = sp.setdiff1d(segs_exon22, segs_exon12)
        elif sp.all(segs_exon12 == segs_exon22):
            seg_diff = sp.setdiff1d(segs_exon11, segs_exon21)
            if seg_diff.shape[0] == 0:
                seg_diff = sp.setdiff1d(segs_exon21, segs_exon11)
        else:
            print >> sys.stderr, "ERROR: both exons differ in alt prime event in verify_alt_prime"
            sys.exit(1)

        # exon_diff_cov
        if seg_diff in segs_exon11 or seg_diff in segs_exon12:
            cov[0] += sp.sum(counts_segments[seg_diff] * seg_lens[seg_diff]) / sp.sum(seg_lens[seg_diff])
        elif seg_diff in segs_exon21 or seg_diff in segs_exon22:
            cov[1] += sp.sum(counts_segments[seg_diff] * seg_lens[seg_diff]) / sp.sum(seg_lens[seg_diff])
        else:
            raise Exception('differential segment not part of any other segment')
        
        ### check intron confirmations as sum of valid intron scores
        ### intron score is the number of reads confirming this intron
        # intron1_conf 
        idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon11[-1], segs_exon12[0]], seg_shape))[0]
        assert(idx.shape[0] > 0)
        cov[0] += counts_edges[idx, 1]
        # intron2_conf 
        idx = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([segs_exon21[-1], segs_exon22[0]], seg_shape))[0]
        assert(idx.shape[0] > 0)
        cov[1] += counts_edges[idx, 1]

    return cov


def quantify_mutex_exons(event, gene, counts_segments, counts_edges, CFG):

    sg = gene.splicegraph
    segs = gene.segmentgraph

    if CFG['is_matlab']:
        seg_lens = segs[0, 0][1, :] - segs[0, 0][0, :]
        seg_shape = segs[0, 2].shape[0]
        order = 'F'
        offset = 1

        ### find exons corresponding to event
        idx_exon_pre  = sp.where((sg[0, 0][0, :] == event.exon_pre[0]) & (sg[0, 0][1, :] == event.exon_pre[1]))[0]
        idx_exon_aft  = sp.where((sg[0, 0][0, :] == event.exon_aft[0]) & (sg[0, 0][1, :] == event.exon_aft[1]))[0]
        idx_exon1  = sp.where((sg[0, 0][0, :] == event.exon1[0]) & (sg[0, 0][1, :] == event.exon1[1]))[0]
        idx_exon2  = sp.where((sg[0, 0][0, :] == event.exon2[0]) & (sg[0, 0][1, :] == event.exon2[1]))[0]
        
        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs[0, 1][idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs[0, 1][idx_exon_aft, :])[1])
        seg_exon1 = sp.sort(sp.where(segs[0, 1][idx_exon1, :])[1])
        seg_exon2 = sp.sort(sp.where(segs[0, 1][idx_exon2, :])[1])

    else:
        seg_lens = segs.segments[1, :] - segs.segments[0, :]
        seg_shape = segs.seg_edges.shape[0]
        order = 'C'
        offset = 0

        ### find exons corresponding to event
        idx_exon_pre  = sp.where((sg.vertices[0, :] == event.exons1[0, 0]) & (sg.vertices[1, :] == event.exons1[0, 1]))[0]
        idx_exon_aft  = sp.where((sg.vertices[0, :] == event.exons1[-1, 0]) & (sg.vertices[1, :] == event.exons1[-1, 1]))[0]
        idx_exon1  = sp.where((sg.vertices[0, :] == event.exons1[1, 0]) & (sg.vertices[1, :] == event.exons1[1, 1]))[0]
        idx_exon2  = sp.where((sg.vertices[0, :] == event.exons2[1, 0]) & (sg.vertices[1, :] == event.exons2[1, 1]))[0]
        
        ### find segments corresponding to exons
        seg_exon_pre = sp.sort(sp.where(segs.seg_match[idx_exon_pre, :])[1])
        seg_exon_aft = sp.sort(sp.where(segs.seg_match[idx_exon_aft, :])[1])
        seg_exon1 = sp.sort(sp.where(segs.seg_match[idx_exon1, :])[1])
        seg_exon2 = sp.sort(sp.where(segs.seg_match[idx_exon2, :])[1])

    # exon1 cov
    cov[0] = sp.sum(counts_segments[seg_exon1] * seg_lens[seg_exon1]) / sp.sum(seg_lens[seg_exon1])
    # exon2 cov
    cov[1] = sp.sum(counts_segments[seg_exon2] * seg_lens[seg_exon2]) / sp.sum(seg_lens[seg_exon2])

    ### check intron confirmation as sum of valid intron scores
    ### intron score is the number of reads confirming this intron
    # exon_pre_exon1_conf
    idx1 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exon1[0]], seg_shape, order=order) + offset)[0]
    if len(idx1.shape) > 0 and idx1.shape[0] > 0:
        cov[0] += counts_edges[idx1[0], 1]
    # exon_pre_exon2_conf
    idx2 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon_pre[-1], seg_exon2[0]], seg_shape, order=order) + offset)[0]
    if len(idx2.shape) > 0 and idx2.shape[0] > 0:
        cov[1] += counts_edges[idx2[0], 1]
    # exon1_exon_aft_conf
    idx3 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon1[-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    if len(idx3.shape) > 0 and idx3.shape[0] > 0:
        cov[0] += counts_edges[idx3[0], 1]
    # exon2_exon_aft_conf
    idx4 = sp.where(counts_edges[:, 0] == sp.ravel_multi_index([seg_exon2[-1], seg_exon_aft[0]], seg_shape, order=order) + offset)[0]
    if len(idx4.shape) > 0 and idx4.shape[0] > 0:
        cov[1] += counts_edges[idx4[0], 1]

    return cov


def quantify_from_counted_events(event_fn, strain_idx=None, event_type=None, CFG=None, out_fn=None):

    ### set parameters if called by rproc
    if strain_idx is None:
        PAR = event_fn
        event_fn = PAR['event_fn']
        strain_idx = PAR['strain_idx']
        if 'out_fn' in PAR:
            out_fn = PAR['out_fn']
        event_type = PAR['event_type']
        CFG = PAR['CFG']

    ### read count_data from event HDF5
    IN = h5py.File(event_fn, 'r', driver='core')
    
    ### get indices of confident events
    if CFG['is_matlab']:
        event_idx = IN['conf_idx'][:].astype('int') - 1
        event_features = IN['event_features'][:]
    else:
        event_idx = IN['conf_idx'][:].astype('int')
        event_features = IN['event_features'][event_type][:]

    ### arrays to collect exon coordinates for length normalization
    pos0e = []
    pos1e = []

    ### get event features we need to include for counting
    if event_type == 'exon_skip':
    #    fidx0e = []
        fidx0i = [sp.where(event_features == 'exon_pre_exon_aft_conf')[0]]
    #    fidx1e = [sp.where(event_features == 'exon_cov')[0]]
        fidx1i = [sp.where(event_features == 'exon_pre_exon_conf')[0], sp.where(event_features == 'exon_exon_aft_conf')[0]] 
    #    pos1e = [IN['event_pos'][[2, 3], :].astype('int')]
    elif event_type == 'intron_retention':
    #    fidx0e = []
        fidx0i = [sp.where(event_features == 'intron_conf')[0]]
    #    fidx1e = [sp.where(event_features == 'intron_cov')[0]]
        fidx1i = []
    #    pos1e = [IN['event_pos'][[1, 2], :].astype('int')]
    elif event_type in ['alt_3prime', 'alt_5prime']:
    #    fidx0e = []
        fidx0i = [sp.where(event_features == 'intron1_conf')[0]]
    #    fidx1e = [sp.where(event_features == 'exon_diff_cov')[0]]
        fidx1i = [sp.where(event_features == 'intron2_conf')[0]]
    #    pos1e = [sp.zeros((IN['event_pos'].shape[0], 2), dtype='int')]
        idx = sp.where(IN['event_pos'][0, :] == IN['event_pos'][2, :])[0]
    #    pos1e[0][idx, :] = IN['event_pos'][[1, 3], :].astype('int')
        idx = sp.where(IN['event_pos'][3, :] == IN['event_pos'][5, :])[0]
    #    pos1e[0][idx, :] = IN['event_pos'][[2, 4], :].astype('int')
    elif event_type == 'mult_exon_skip':
    #    fidx0e = []
        fidx0i = [sp.where(event_features == 'exon_pre_exon_aft_conf')[0]]
    #    fidx1e = [sp.where(event_features == 'exons_cov')[0]]
        fidx1i = [sp.where(event_features == 'exon_pre_exon_conf')[0], sp.where(event_features == 'exon_exon_aft_conf')[0], sp.where(event_features == 'sum_inner_exon_conf')[0]] 
        tmp_idx = sp.where(event_features == 'len_inner_exon')[0]
    #    pos1e = [sp.c_[sp.zeros((IN['event_counts'].shape[0],), dtype='int'), IN['event_counts'][:, tmp_idx, 0].astype('int')]]
    elif event_type == 'mutex_exons':
    #    fidx0e = [sp.where(event_features == 'exon1_cov')[0]]
        fidx0i = [sp.where(event_features == 'exon_pre_exon1_conf')[0], sp.where(event_features == 'exon1_exon_aft_conf')[0]]
    #    fidx1e = [sp.where(event_features == 'exon2_cov')[0]]
        fidx1i = [sp.where(event_features == 'exon_pre_exon2_conf')[0], sp.where(event_features == 'exon2_exon_aft_conf')[0]] 
    #    pos0e = [IN['event_pos'][[2, 3], :].astype('int')]
    #    pos1e = [IN['event_pos'][[4, 5], :].astype('int')]
    else:
        raise Error('Event type %s either not known or not implemented for testing yet' % event_type)

    ### init coverage matrix
    cov = [sp.zeros((event_idx.shape[0], strain_idx.shape[0]), dtype='float'), sp.zeros((event_idx.shape[0], strain_idx.shape[0]), dtype='float')]

    ### get counts for exon segments
    #if CFG['verbose']:
    #    print 'Collecting exon segment expression values'
    #for f, ff in enumerate(fidx0e):
    #    cov[0] += (IN['event_counts'][:, ff[0], strain_idx][event_idx, :] * (pos0e[f][1, event_idx] - pos0e[f][0, event_idx])[:, sp.newaxis]) / CFG['read_length']
    #for f, ff in enumerate(fidx1e):
    #    cov[1] += (IN['event_counts'][:, ff[0], strain_idx][event_idx, :] * (pos1e[f][1, event_idx] - pos1e[f][0, event_idx])[:, sp.newaxis]) / CFG['read_length']

    ### get counts for introns
    if CFG['verbose']:
        print 'Collecting intron confirmation values'

    ### get gene index
    if CFG['is_matlab']:
        gene_idx = IN['gene_idx'][:].astype('int') - 1
        for f in fidx0i:
            cov[0] += IN['event_counts'][:, f[0], strain_idx][event_idx, :]
        for f in fidx1i:
            cov[1] += IN['event_counts'][:, f[0], strain_idx][event_idx, :]
    else:
        gene_idx = IN['gene_idx'][:].astype('int')
        for f in fidx0i:
            cov[0] += IN['event_counts'][strain_idx, f[0], :][:, event_idx].T
        for f in fidx1i:
            cov[1] += IN['event_counts'][strain_idx, f[0], :][:, event_idx].T

    ### get strain list
    strains = IN['strains'][:]

    IN.close()

    ### only keep confident events
    gene_idx = gene_idx[event_idx]

    return (cov, gene_idx, event_idx, strains)


def quantify_from_graph(ev, strain_idx=None, event_type=None, CFG=None, out_fn=None, fn_merge=None):
    # cov = quantify_from_graph(ev, strain_idx, event_type, CFG, out_fn)

    ### set parameters if called by rproc
    if strain_idx is None:
        PAR = ev
        ev = PAR['ev']
        strain_idx = PAR['strain_idx']
        if 'out_fn' in PAR:
            out_fn = PAR['out_fn']
        event_type = PAR['event_type']
        CFG = PAR['CFG']

    if fn_merge is None:
        fn_merge = get_filename('fn_out_merge_val', CFG)

    if CFG['is_matlab']:
        genes = scio.loadmat(fn_merge, struct_as_record=False)['genes'][0, :]
        fn_count = fn_merge.replace('mat', 'count.mat')
    else:
        genes = cPickle.load(open(fn_merge_val, 'r'))[0]
        fn_count = fn_merge.replace('pickle', 'count.pickle')

    ### load count index data from hdf5
    IN = h5py.File(fn_count, 'r')
    gene_ids_segs = IN['gene_ids_segs'][:].astype('int')
    gene_ids_edges = IN['gene_ids_edges'][:].astype('int')
    if len(gene_ids_segs.shape) > 1:
        gene_ids_segs = gene_ids_segs[0, :]
    if len(gene_ids_edges.shape) > 1:
        gene_ids_edges = gene_ids_edges[0, :]

    ### sort events by gene idx
    s_idx = sp.argsort([x.gene_idx for x in ev])
    ev = ev[s_idx]
    old_idx = sp.argsort(s_idx)

    ### find gene idx boundaries
    assert(isequal(gene_ids_segs, sp.sort(gene_ids_segs)))
    assert(isequal(gene_ids_edges, sp.sort(gene_ids_edges)))

    tmp, genes_f_idx_segs = sp.unique(gene_ids_segs, return_index=True)
    genes_l_idx_segs = sp.r_[genes_f_idx_segs[1:] - 1, gene_ids_segs.shape[0]]

    tmp, genes_f_idx_edges = sp.unique(gene_ids_edges, return_index=True)
    genes_l_idx_edges = sp.r_[genes_f_idx_edges[1:] - 1, gene_ids_edges.shape[0]]

    gr_idx_segs = 0
    gr_idx_edges = 0
    counts = []
    for i in range(ev.shape[0]):
        sys.stdout.write('.')
        if i % 10 == 0:
            sys.stdout.write('%i\n' % i)
        sys.stdout.flush()
        if CFG['is_matlab']:
            offset = 1
        else:
            offset = 0
        g_idx = ev[i].gene_idx

        while gene_ids_segs[genes_f_idx_segs[gr_idx_segs]] < g_idx:
            gr_idx_segs += 1
        assert(gene_ids_segs[genes_f_idx_segs[gr_idx_segs]] == g_idx)

        while gene_ids_edges[genes_f_idx_edges[gr_idx_edges]] < g_idx:
            gr_idx_edges += 1
        assert(gene_ids_edges[genes_f_idx_edges[gr_idx_edges]] == g_idx)

        ### laod relevant count data from HDF5
        if CFG['is_matlab']:
            segments = IN['segments'][strain_idx, genes_f_idx_segs[gr_idx_segs]:genes_l_idx_segs[gr_idx_segs] + 1].T
            seg_pos = IN['seg_pos'][strain_idx, genes_f_idx_segs[gr_idx_segs]:genes_l_idx_segs[gr_idx_segs] + 1].astype('int')
            edges = IN['edges'][strain_idx, genes_f_idx_edges[gr_idx_edges]:genes_l_idx_edges[gr_idx_edges] + 1].T
            edge_idx = IN['edge_idx'][0, genes_f_idx_edges[gr_idx_edges]:genes_l_idx_edges[gr_idx_edges] + 1].astype('int')
        else:
            segments = IN['segments'][genes_f_idx_segs[gr_idx_segs]:genes_l_idx_segs[gr_idx_segs]+1, strain_idx]
            seg_pos = IN['seg_pos'][genes_f_idx_segs[gr_idx_segs]:genes_l_idx_segs[gr_idx_segs]+1, strain_idx]
            edges = IN['edges'][genes_f_idx_edges[gr_idx_edges]:genes_l_idx_edges[gr_idx_edges]+1, strain_idx]
            edge_idx = IN['edge_idx'][genes_f_idx_edges[gr_idx_edges]:genes_l_idx_edges[gr_idx_edges]+1]

        for s_idx in range(len(strain_idx)):
            #print '%i/%i' % (s_idx, len(strain_idx))

            if event_type == 'exon_skip':
                cov = quantify_exon_skip(ev[i], genes[g_idx - offset], segments[:, s_idx].T,  sp.c_[edge_idx, edges[:, s_idx]], CFG)
            elif event_type in ['alt_3prime', 'alt_5prime']:
                cov = quantify_alt_prime(ev[i], genes[g_idx - offset], segments[:, s_idx].T,  sp.c_[edge_idx, edges[:, s_idx]], CFG)
            elif event_type == 'intron_retention':
                cov = quantify_intron_retention(ev[i], genes[g_idx - offset], segments[:, s_idx].T,  sp.c_[edge_idx, edges[:, s_idx]], seg_pos[:, s_idx].T, CFG)
            elif event_type == 'mult_exon_skip':
                cov = quantify_mult_exon_skip(ev[i], genes[g_idx - offset], segments[:, s_idx].T,  sp.c_[edge_idx, edges[:, s_idx]], CFG)
            elif event_type == 'mutex_exons':
                cov = quantify_mutex_exons(ev[i], genes[g_idx - offset], segments[:, s_idx].T,  sp.c_[edge_idx, edges[:, s_idx]], CFG)

            if s_idx == 0:
                counts.append(sp.array([cov]))
            else:
                counts[-1] = sp.r_[counts[-1], sp.array([cov])]
    IN.close()
    counts = sp.dstack(counts)

    ### re-sort by old idx
    ev = ev[old_idx]
    counts = counts[:, :, old_idx]

    if out_fn is not None:
        cPickle.dump((ev, counts), open(out_fn, 'w'))

    return (ev, counts)
