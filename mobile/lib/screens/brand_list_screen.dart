import 'package:flutter/material.dart';

import '../api.dart';
import '../profile.dart';
import 'brand_screen.dart';

/// Brand-first browsing (PRD FR-3.1): searchable, alphabetical brand list.
class BrandListScreen extends StatefulWidget {
  const BrandListScreen({
    super.key,
    required this.api,
    required this.store,
    required this.profile,
  });

  final ApiClient api;
  final ProfileStore store;
  final Profile profile;

  @override
  State<BrandListScreen> createState() => _BrandListScreenState();
}

class _BrandListScreenState extends State<BrandListScreen> {
  late Future<List<Map<String, dynamic>>> _brands;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _brands = widget.api.brands(gender: widget.profile.gender);
  }

  void _retry() {
    setState(() => _brands = widget.api.brands(gender: widget.profile.gender));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Značky')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Hledat značku',
                border: OutlineInputBorder(),
              ),
              onChanged: (v) => setState(() => _query = v.trim().toLowerCase()),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: _brands,
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Značky se nepodařilo načíst: ${snapshot.error}'),
                        TextButton(onPressed: _retry, child: const Text('Zkusit znovu')),
                      ],
                    ),
                  );
                }
                final brands = snapshot.data;
                if (brands == null) {
                  return const Center(child: CircularProgressIndicator());
                }
                final visible = [
                  for (final b in brands)
                    if (_query.isEmpty ||
                        (b['brand_name'] as String).toLowerCase().contains(_query))
                      b,
                ];
                if (visible.isEmpty) {
                  return const Center(child: Text('Žádná značka neodpovídá hledání.'));
                }
                return ListView.separated(
                  itemCount: visible.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    final b = visible[i];
                    return ListTile(
                      title: Text(b['brand_name'] as String),
                      subtitle: Text(_segmentName(b['segment'] as String?)),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => BrandScreen(
                          api: widget.api,
                          store: widget.store,
                          profile: widget.profile,
                          brand: b,
                        ),
                      )),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

String _segmentName(String? segment) => const {
      'fast_fashion': 'Rychlá móda',
      'mass_market': 'Masový trh',
      'mid_market': 'Střední třída',
      'private_label': 'Privátní značka',
      'premium': 'Prémiová',
      'luxury': 'Luxusní',
      'sportswear': 'Sport',
      'outdoor': 'Outdoor',
      'denim': 'Džíny',
      'footwear': 'Obuv',
      'lingerie': 'Spodní prádlo',
      'menswear': 'Pánská móda',
      'basics': 'Základní oblečení',
    }[segment] ??
    (segment ?? '');
