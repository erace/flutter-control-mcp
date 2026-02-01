import 'package:flutter/material.dart';
import 'package:flutter_driver/driver_extension.dart';

void main() {
  // Automatically enable Flutter Driver in debug builds only.
  // This allows automation testing while having zero overhead in release builds.
  // The assert block is tree-shaken out in release mode.
  assert(() {
    enableFlutterDriverExtension();
    return true;
  }());

  runApp(const FlutterControlTestApp());
}

class FlutterControlTestApp extends StatelessWidget {
  const FlutterControlTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Control Test',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const TestHomePage(),
    );
  }
}

class TestHomePage extends StatefulWidget {
  const TestHomePage({super.key});

  @override
  State<TestHomePage> createState() => _TestHomePageState();
}

class _TestHomePageState extends State<TestHomePage> {
  int _counter = 0;
  String _inputText = '';
  String _statusMessage = 'Ready';

  void _incrementCounter() {
    setState(() {
      _counter++;
      _statusMessage = 'Counter incremented';
    });
  }

  void _decrementCounter() {
    setState(() {
      _counter--;
      _statusMessage = 'Counter decremented';
    });
  }

  void _resetCounter() {
    setState(() {
      _counter = 0;
      _statusMessage = 'Counter reset';
    });
  }

  void _onSubmit() {
    setState(() {
      _statusMessage = 'Submitted: $_inputText';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Flutter Control Test'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Counter section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text('Counter', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    Text(
                      '$_counter',
                      key: const Key('count_label'),
                      style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold),
                      semanticsLabel: 'Count is $_counter',
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        ElevatedButton(
                          key: const Key('decrement_btn'),
                          onPressed: _decrementCounter,
                          child: const Text('Decrement'),
                        ),
                        ElevatedButton(
                          key: const Key('increment_btn'),
                          onPressed: _incrementCounter,
                          child: const Text('Increment'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      key: const Key('reset_btn'),
                      onPressed: _resetCounter,
                      child: const Text('Reset'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Text input section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text('Text Input', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    TextField(
                      key: const Key('input_field'),
                      decoration: const InputDecoration(labelText: 'Enter text', border: OutlineInputBorder()),
                      onChanged: (value) => setState(() => _inputText = value),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      key: const Key('submit_btn'),
                      onPressed: _onSubmit,
                      child: const Text('Submit'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Status section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text('Status', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text(_statusMessage, key: const Key('status_label'), style: const TextStyle(fontSize: 16)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Scrollable list
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text('Scrollable List', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 200,
                      child: ListView.builder(
                        key: const Key('test_list'),
                        itemCount: 20,
                        itemBuilder: (context, index) {
                          return ListTile(
                            key: Key('list_item_$index'),
                            title: Text('Item ${index + 1}'),
                            onTap: () => setState(() => _statusMessage = 'Tapped Item ${index + 1}'),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
