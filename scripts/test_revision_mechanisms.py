#!/usr/bin/env python3
"""Deterministic Phase-1 checks; no campaign, process pool or output publication."""
import math
import unittest
from unittest.mock import patch

import networkx as nx
import numpy as np
import pandas as pd

import run_revision_campaign as campaign


class RevisionMechanisms(unittest.TestCase):
    def test_strict_dwell_hold_in_both_entrypoints(self):
        for entry in (campaign.run_control_plane_diagnostic, campaign.run_control_plane_relaxation):
            graph = nx.star_graph(5)
            with patch.object(campaign, 'compute_routing_tables', wraps=campaign.compute_routing_tables) as route, \
                 patch.object(campaign, 'compute_structural_stress', wraps=campaign.compute_structural_stress) as sense:
                result = entry(graph, 'Full_SRA', dwell_time=5, max_iters=13, record_trace=True)
            self.assertEqual(route.call_count, 4)  # initial install + k=0,5,10
            self.assertEqual(sense.call_count, 8)  # initial/final + feedback/metric at boundaries
            trace = result['trace']
            for previous, current in zip(trace, trace[1:]):
                if current['k'] % 5:
                    self.assertFalse(current['active'])
                    self.assertEqual(current['paths_sig'], previous['paths_sig'])
                    self.assertEqual(current['q'], previous['q'])
                    for u in graph:
                        self.assertAlmostEqual(current['S'][u], .9*previous['S'][u]+.1*current['q'][u])
                        self.assertAlmostEqual(current['C'][u], 1+10*current['S'][u])
                    self.assertGreater(current['S'][0], previous['S'][0])
            self.assertEqual(result['iters_executed'], 13)
            self.assertEqual(result['switch_rate'], result['switch_count']/13)
            self.assertEqual(result['tail_switch_rate'], np.mean(result['switch_history'][-50:]))

    def test_boundary_early_stopping_and_fixed_timing_sample(self):
        for entry in (campaign.run_control_plane_diagnostic, campaign.run_control_plane_relaxation):
            result = entry(nx.star_graph(4), 'Full_SRA', max_iters=200, record_trace=True)
            self.assertTrue(result['converged_early'])
            self.assertLess(result['iters_executed'], 200)
            final = result['trace'][-1]
            self.assertEqual(final['k'] % 5, 0)
            self.assertLessEqual(final['max_abs_delta_S'], 1e-5)
            self.assertEqual(final['paths_sig'], result['trace'][-2]['paths_sig'])
        timing = campaign.run_control_plane_relaxation(nx.star_graph(4), 'Full_SRA', measure_runtime=True)
        self.assertEqual(timing['iters_executed'], 50)
        self.assertEqual(len(timing['recompute_times_ms']), 10)
        self.assertFalse(timing['converged_early'])
        self.assertEqual(timing['eval_ms'], np.mean(timing['recompute_times_ms']))
        self.assertEqual(timing['amortized_iter_ms'], timing['loop_total_ms']/50)

    def test_even_block_tail_and_oscillating_orbit(self):
        graph = nx.cycle_graph(4)
        phases = [campaign.compute_routing_tables(graph.copy(), costs) for costs in
                  ({0: 1., 1: 1., 2: 1., 3: 10.},
                   {0: 1., 1: 10., 2: 1., 3: 1.})]
        capacities = {0: 2, 1: 3, 2: 4, 3: 5}
        demand = {(0, 2): 9., (2, 0): 9.}
        for dwell, blocks in ((1, 12), (3, 12), (5, 12), (10, 12), (5, 4), (5, 1)):
            with self.subTest(dwell=dwell, blocks=blocks):
                installs = []
                def alternate(*args, **kwargs):
                    # Initial solve, then alternating installed blocks.
                    phase = phases[max(0, len(installs)-1) % 2]
                    installs.append(phase)
                    return phase
                iters = dwell * blocks - 1
                with patch.object(campaign, 'compute_routing_tables', side_effect=alternate):
                    result = campaign.run_control_plane_relaxation(
                        graph, 'Weighted_SRA', dwell_time=dwell, max_iters=iters,
                        demand_matrix=demand, node_capacities=capacities)
                self.assertFalse(result['converged_early'])
                self.assertEqual(result['dwell_time_used'], dwell)
                expected_tables = [rt for rt, _ in installs[1:]][-8:]
                self.assertEqual(result['orbit_routing_tables'], expected_tables)
                self.assertIs(result['orbit_routing_tables'][-1], result['routing_tables'])
                expected_gen, expected_peak = [], []
                for _, paths in installs[1:]:
                    generalized = campaign.compute_structural_stress(
                        graph, paths, demand_matrix=demand, node_capacities=capacities)
                    raw = campaign.compute_structural_stress(graph, paths, demand_matrix=demand)
                    expected_gen.extend([max(generalized.values())] * dwell)
                    expected_peak.extend([max(raw.values())] * dwell)
                expected_gen, expected_peak = expected_gen[:iters], expected_peak[:iters]
                self.assertEqual(result['gen_peak_trace'], expected_gen)
                tail_len = min(iters, max(8, 2 * math.ceil(20 / dwell)) * dwell)
                self.assertAlmostEqual(result['tail_max_generalized_stress'],
                                       float(np.mean(expected_gen[-tail_len:])))
                self.assertAlmostEqual(result['final_peak_bc'], float(np.mean(expected_peak[-tail_len:])))
                self.assertEqual(result['last_snapshot_peak_bc'], expected_peak[-1])
                self.assertAlmostEqual(result['peak_reduction_pct'],
                                       (result['initial_peak_bc'] - result['final_peak_bc']) /
                                       max(result['initial_peak_bc'], 1e-9) * 100.)

    def test_single_table_orbits(self):
        graph = nx.star_graph(4)
        for variant in ('Dijkstra', 'Static_BC', 'Full_SRA'):
            result = campaign.run_control_plane_relaxation(
                graph.copy(), variant, max_iters=200, node_capacities=dict.fromkeys(graph, 3))
            self.assertEqual(result['orbit_routing_tables'], [result['routing_tables']])
            if variant == 'Full_SRA':
                self.assertTrue(result['converged_early'])
            expected = campaign.compute_structural_stress(
                graph, result['all_paths'], node_capacities=dict.fromkeys(graph, 3))
            self.assertAlmostEqual(result['tail_max_generalized_stress'], max(expected.values()))
            self.assertEqual(result['final_peak_bc'], np.mean(result['peak_trace']))
        result = campaign.run_control_plane_relaxation(graph, 'Reactive_BC_alpha1', dwell_time=5, max_iters=1)
        self.assertEqual(result['dwell_time_used'], 1)
        self.assertEqual(result['gen_peak_trace'], result['peak_trace'])

    def test_packet_orbit_replay(self):
        visits = []
        class ObservedTable(dict):
            def __init__(self, phase):
                super().__init__({0: {1: 1}, 1: {0: 0}})
                self.phase = phase
            def get(self, node, default=None):
                visits.append(self.phase)
                return super().get(node, default)
        graph = nx.path_graph(2)
        initial, _ = campaign.compute_routing_tables(graph, dict.fromkeys(graph, 1.))
        orbit = [ObservedTable(i) for i in range(3)]
        for interval in (1, 2, 5):
            visits.clear()
            with patch.object(campaign.np.random, 'default_rng') as make_rng:
                rng = make_rng.return_value
                rng.poisson.return_value = 1
                rng.choice.return_value = [0]  # One 0 -> 1 packet per timestep.
                result = campaign.run_packet_simulation(
                    graph, initial, total_steps=17, warmup_steps=0,
                    demand_weights={(0, 1): 1., (1, 0): 0.},
                    orbit_routing_tables=orbit, orbit_step_interval=interval)
            self.assertEqual(visits, [(t // interval) % len(orbit) for t in range(17)])
            self.assertGreater(result['pdr'], 0.)

    def test_ab_grid_flag_defaults_off(self):
        class ParserCaptured(Exception):
            pass
        def capture(parser):
            self.assertFalse(parser.parse_args(['--out-dir', '/tmp/unused']).include_ab_grid)
            self.assertTrue(parser.parse_args(['--out-dir', '/tmp/unused', '--include-ab-grid']).include_ab_grid)
            raise ParserCaptured
        original_parse = campaign.argparse.ArgumentParser.parse_args
        def intercept(parser):
            # Parse the actual main parser without entering any campaign work.
            with patch.object(campaign.argparse.ArgumentParser, 'parse_args', original_parse):
                capture(parser)
        with patch.object(campaign.argparse.ArgumentParser, 'parse_args', intercept):
            with self.assertRaises(ParserCaptured):
                campaign.main()

    def test_memoryless_and_damped_ft(self):
        for variant in ('IGP_Weight_Tuning', 'IGP_Damped_FT'):
            result = campaign.run_control_plane_diagnostic(nx.star_graph(4), variant, max_iters=1, record_trace=True)
            step = result['trace'][0]
            for u, util in step['q'].items():
                penalty = campaign.fortz_thorup_penalty(util)
                expected = penalty if variant == 'IGP_Weight_Tuning' else .7 + .3*penalty
                self.assertAlmostEqual(step['C'][u], expected)
            if variant == 'IGP_Weight_Tuning':
                self.assertNotEqual(step['C'][0], .7+.3*campaign.fortz_thorup_penalty(1))

    def test_static_one_shot_install_at_k1(self):
        graph = nx.barabasi_albert_graph(10, 2, seed=4)
        unit = dict.fromkeys(graph, 1.)
        _, paths = campaign.compute_routing_tables(graph, unit)
        bc = campaign.compute_structural_stress(graph, paths)
        expected_cost = {u: 1+10*bc[u]/max(bc.values()) for u in graph}
        expected_rt, _ = campaign.compute_routing_tables(graph, expected_cost)
        with patch.object(campaign, 'compute_routing_tables', wraps=campaign.compute_routing_tables) as route:
            result = campaign.run_control_plane_diagnostic(graph, 'Static_BC', max_iters=10)
        self.assertEqual(route.call_count, 2)
        self.assertEqual(result['node_costs'], expected_cost)
        self.assertEqual(result['routing_tables'], expected_rt)
        self.assertTrue(all(not value for i, value in enumerate(result['switch_history']) if i != 1))
        self.assertFalse(result['converged_early'])

    def test_capacity_alignment(self):
        graph = nx.path_graph(3)
        capacities = {0: 3.4, 1: 4.6, 2: 10.8}
        rt, paths = campaign.compute_routing_tables(graph, dict.fromkeys(graph, 1.))
        raw = campaign.compute_structural_stress(graph, paths)
        weighted = campaign.compute_structural_stress(graph, paths, node_capacities=capacities)
        packet = campaign.run_packet_simulation(graph, rt, node_capacities=capacities, total_steps=25, warmup_steps=0)
        for u in graph:
            self.assertEqual(packet['proc_cap'][u], int(round(capacities[u])))
            self.assertAlmostEqual(weighted[u], raw[u]/packet['proc_cap'][u])
        generated = campaign.heterogeneous_capacities(range(100), np.random.default_rng(12))
        self.assertEqual(sum(v <= 5 for v in generated.values()), 35)
        self.assertTrue(all(3 <= v <= 5 or 10 <= v <= 16 for v in generated.values()))

    def test_experiment_comparators_and_horizons(self):
        graph = nx.barabasi_albert_graph(6, 2, seed=3)
        dummy = dict(throughput=1., pdr=.9, drop_rate=.1, avg_latency=2.,
                     p95_latency=3., avg_hops=2.)
        with patch.object(campaign.nx, 'barabasi_albert_graph', return_value=graph), \
             patch.object(campaign, 'run_packet_simulation', return_value=dummy) as packet, \
             patch.object(campaign, 'run_control_plane_diagnostic', wraps=campaign.run_control_plane_diagnostic) as cp:
            exp1 = campaign.worker_exp1_trial(('BA', 7, .9))
            self.assertEqual(len(exp1), 9)
            self.assertIn('IGP_Damped_FT', {row['method'] for row in exp1})
            exp2 = campaign.worker_exp2_hetero_noise((7, 0.))
            self.assertEqual(len(exp2), 6)
            noisy = campaign.worker_exp2_hetero_noise((7, .1))
            self.assertEqual({row['method'] for row in noisy}, {
                'Dijkstra', 'Static_BC', 'Reactive_BC_alpha1',
                'Topology_Only_SRA', 'Generalized_Weighted_SRA'})
            campaign.worker_exp3_dwell((7, 5, .1, 10.))
            for call in packet.call_args_list:
                self.assertEqual(call.kwargs['total_steps'], 1000)
                self.assertEqual(call.kwargs['warmup_steps'], 200)
                self.assertTrue(call.kwargs['orbit_routing_tables'])
                self.assertGreater(call.kwargs['orbit_step_interval'], 0)
            for call in cp.call_args_list:
                self.assertEqual(call.kwargs['max_iters'], 200)
            hetero_calls = [call for call in packet.call_args_list if 'node_capacities' in call.kwargs]
            self.assertTrue(all(isinstance(v, int) for call in hetero_calls
                                for v in call.kwargs['node_capacities'].values()))

    def test_tv_fair_start_and_hotspot_shift(self):
        # Exercise all 1000 steps on a small fixture; inspect the real packet calls.
        graph = nx.barabasi_albert_graph(8, 2, seed=8)
        real_packet = campaign.run_packet_simulation
        calls = []
        def observe(*args, **kwargs):
            result = real_packet(*args, **kwargs)
            calls.append((args, kwargs, result))
            return result
        with patch.object(campaign.nx, 'barabasi_albert_graph', return_value=graph), \
             patch.object(campaign, 'run_packet_simulation', side_effect=observe), \
             patch.object(campaign, 'run_control_plane_diagnostic', side_effect=AssertionError('No prewarm')):
            result = campaign.worker_tv_trial(11)
        methods = ['Dijkstra', 'Static_BC', 'Reactive_BC', 'Topology_SRA', 'Weighted_SRA']
        self.assertTrue(set(methods).issubset(result))
        for method, (args, kwargs, packet) in zip(methods, calls):
            self.assertEqual([point[0] for point in result[method]], list(range(25, 1001, 25)))
            self.assertEqual(kwargs['load_schedule'], {0:.6, 350:1.1, 700:.7})
            self.assertNotEqual(kwargs['demand_weights'], kwargs['demand_schedule'][350])
            self.assertEqual(sorted(kwargs['demand_weights'].values()), sorted(kwargs['demand_schedule'][350].values()))
            self.assertTrue(0 <= packet['online_switch_rate'] <= 1)
            if method in ('Reactive_BC', 'Topology_SRA', 'Weighted_SRA'):
                self.assertNotIn('init_costs', kwargs['sra_online_params'])
                self.assertTrue(all(cost == 1. for cost in packet['initial_online_costs'].values()))
                self.assertEqual(args[1], calls[0][0][1])
            else:
                self.assertEqual(packet['online_switch_rate'], 0.)

    def test_exp4_cross_scale_and_protocol(self):
        for size in (6, 9):
            with patch.object(campaign, 'run_packet_simulation', wraps=campaign.run_packet_simulation) as packet:
                rows = campaign.worker_exp4_scalability(('BA', size, 19))
            self.assertEqual({row['method'] for row in rows}, {'Full_SRA', 'Unnormalized_SRA'})
            self.assertTrue(all(row['N'] == size for row in rows))
            for call in packet.call_args_list:
                self.assertEqual(call.kwargs['total_steps'], 1000)
                self.assertEqual(call.kwargs['warmup_steps'], 200)
                self.assertTrue(call.kwargs['orbit_routing_tables'])
                self.assertGreater(call.kwargs['orbit_step_interval'], 0)
            self.assertTrue(all(math.isfinite(row['throughput']) for row in rows))

    def test_paired_statistics(self):
        frame = pd.DataFrame([dict(seed=seed, method=method, throughput=value)
                              for seed in range(1, 7)
                              for method, value in [('Full', seed+2), ('Other', seed), ('Equal', seed+2)]])
        stats = campaign.paired_statistics(frame.sample(frac=1, random_state=2), 'Full', ('throughput',))
        self.assertEqual(stats['Other']['throughput']['mean_diff'], 2.)
        self.assertEqual(stats['Other']['throughput']['ci95_diff'], 0.)
        self.assertEqual(stats['Equal']['throughput']['wilcoxon_p_raw'], 1.)
        self.assertGreaterEqual(stats['Other']['throughput']['holm_p'], stats['Other']['throughput']['wilcoxon_p_raw'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
