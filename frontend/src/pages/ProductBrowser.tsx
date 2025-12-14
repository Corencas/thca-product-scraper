import { useState, useEffect } from 'react';

interface Product {
  id: number;
  title: string;
  url: string;
  vendor_name: string;
  current_price?: number;
  in_stock: boolean;
}

export default function ProductBrowser() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/products?limit=50');
      const data = await response.json();
      setProducts(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching products:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Loading products...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-green-400">
          THCA Community Platform
        </h1>
        
        <div className="mb-4 text-slate-400">
          {products.length} products found
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map(product => (
            <div key={product.id} className="bg-slate-900 rounded-lg p-4 border border-slate-800 hover:border-green-500 transition">
              <h3 className="font-semibold mb-2 text-white line-clamp-2">
                {product.title}
              </h3>
              
              <div className="text-sm text-slate-400 mb-2">
                {product.vendor_name}
              </div>
              
              {product.current_price && (
                <div className="text-green-400 font-bold mb-2">
                  ${product.current_price.toFixed(2)}
                </div>
              )}
              
              <div className="mb-3">
                {product.in_stock ? (
                  <span className="px-2 py-1 bg-green-900/50 text-green-300 text-xs rounded-full">
                    In Stock
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-red-900/50 text-red-300 text-xs rounded-full">
                    Out of Stock
                  </span>
                )}
              </div>
              
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full text-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
              >
                View Product
              </a>
            </div>
          ))}
        </div>

        {products.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            No products found yet. The product watcher will add products soon!
          </div>
        )}
      </div>
    </div>
  );
}
